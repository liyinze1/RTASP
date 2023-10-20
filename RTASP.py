import random
import socket
from threading import Thread
from queue import Queue
import time
import cbor2

len_v = 1
len_cc = 1
len_pt = 1
len_csrc = 1
len_id = 2
len_ts = 2
len_sn = 2

len_header = len_v + len_cc + len_pt + len_csrc + len_id + len_ts + len_sn

STOP = int.to_bytes(0, 1)
START = int.to_bytes(1, 1)
SLOWER = int.to_bytes(2, 1)
FASTER = int.to_bytes(3, 1)
DISCOVER = int.to_bytes(4, 1)
CONFIG = int.to_bytes(5, 1)
MULTI = int.to_bytes(6, 1)

# window_size = 1000

# len_len = 2
    

class RTCASP_sender:
    def __init__(self, dest_ip: str='127.0.0.1', dest_port: int=23000):
        self.sensor_list = []
        assert dest_port % 2 == 0
        
        self.dest_ip = dest_ip
        self.dest_port = dest_port
        
        self.control_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.control_sock.bind(('0.0.0.0', dest_port + 1))
        
        self.control_thread = Thread(target=self.__control_channel_receive)
        self.control_thread.start()
        
        self.start_transmit = False
        
    
    def __control_channel_receive(self):
        while True:
            msg, addr = self.control_sock.recvfrom(2048)
            print(addr)
            if addr[0] == self.dest_ip:
                self.__control_msg_analysis(msg)
                    
                    
    def __control_msg_analysis(self, msg):
        opt = msg[0]
        if opt == START:
            if msg[1:] == self.session_id:
                self.start_transmit = True
        elif opt == STOP:
            self.start_transmit = False
        elif opt == FASTER:
            pass
        elif opt == SLOWER:
            pass
        elif opt == CONFIG:
            sensor = cbor2.loads(msg[1:])
            for i, s in enumerate(self.sensor_list):
                if s['id'] == sensor['id']:
                    self.sensor_list[i] = sensor
        elif opt == DISCOVER:
            self.send_configuration()
        elif opt == MULTI:
            i = 1
            msg_list = []
            while i < len(msg):
                size = msg[i]
                i += 1
                msg_list.append(msg[i: i + size])
                i += size
        
    def send_configuration(self):
        reply = bytes()
        for sensor in self.sensor_list:
            encoded_sensor = cbor2.dumps(sensor)
            reply += len(encoded_sensor).to_bytes(1) + encoded_sensor
        self.control_send(reply)
        
    def control_send(self, msg):
        self.control_sock.sendto(msg, (self.dest_ip, self.dest_port))
        
    def register(self, id, type, reservation, sample_rate, power_comsumption):
        sensor = {'id': id, 'tp': type, 'rsv': reservation, 'sr': sample_rate, 'pwr': power_comsumption}
        self.sensor_list.append(sensor)
        
    def configure(self, id, type, reservation, sample_rate, power_comsumption):
        for i, sensor in enumerate(self.sensor_list):
            if id == sensor.id:
                self.sensor_list[i] = {'id': id, 'tp': type, 'rsv': reservation, 'sr': sample_rate, 'pwr': power_comsumption}
        
    def start(self):
        self.session_id = random.randint(0, 65535).to_bytes(len_id, 'big')
        if self.start_transmit:
            return True
        for i in range(5):
            self.control_send(START + self.session_id)
            time.sleep(2)
            if self.start_transmit:
                # start
                self.sender = RTCASP_sender()
                self.send_configuration()
        print('time out! cannot connect to server')
        return False
    
    def stop(self):
        if not self.start_transmit:
            return
        self.start_transmit = False
        self.control_send(STOP)
        
    def send_packet(self, data):
        self.sender.send(data)

class RTASP_sender:
    def __init__(self, version: int=0, dest_ip: str='127.0.0.1', dest_port: int=23000, session_id: int=None):
        assert dest_port % 2 == 0
        self.v = version.to_bytes(len_v, 'big') # 8 bit version number

        if session_id == None:
            self.id = random.randint(0, 65535).to_bytes(len_id, 'big') # random stream id
        else:
            self.id = session_id
        self.sn = 0
        
        self.dest_addr = (dest_ip, dest_port)
        self.dest_ip = dest_ip
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('0.0.0.0', dest_port + 1))
        
        self.timestamp = 0
        self.__clock_thread = Thread(target=self.__clock)
        self.__clock_thread.start()
        
    def __clock(self):
        time.sleep(1)
        self.timestamp += 1
        
    def send(self, csrc: bytes, payload: bytes):
        # self.__transmit_queue.put((index, payload))
        self.sn %= 65536

        packet = self.v + self.id + csrc+ self.timestamp.to_bytes(len_ts) + self.sn.to_bytes(len_sn, 'big') + payload
        self.sn += 1
        
        self.sock.sendto(packet, self.dest_addr)
        
        return packet
            
class Window_buffer:
    def __init__(self, window_size: int=1000):
        self.window_size = window_size
        # self.window = [None] * window_size
        self.window = [None]
        self.offset = 0
        self.count = 0
    
    def update(self, data):
        self.count += 1
        sn = data['sn']
        if sn >= len(self.window):
            self.window += [None] * (sn - len(self.window))
            self.window.append(data)
        else:
            self.window[sn] = data
    
    def loss_rate(self):
        return 1 - self.count / len(self.window)
        
    def stop(self):
        return self.window

class RTASP_receiver:
    def __init__(self, ip: str='0.0.0.0', port: int=23000):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.port = port
        self.sock.bind((ip, port))
        self.window_dict = {}
        self.data_dict = {}
        
        self.count = 0
        
        self.qos_freq = 1 / 10
        self.qos_queue_upper = 10000
        self.qos_queue_lower = 1000
        
        self.transmit_freq = 1e-3
        
        self.__receive_thread = Thread(target=self.__receive)
        self.__buffer_thread = Thread(target=self.__buffer_window)
        self.__print_thread = Thread(target=self.__print)
        self.__qos_thread = Thread(target=self.__qos)
        
        self.__queue = Queue()
        
        # control channel
        self.control_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.control_sock.bind((ip, port + 1))
        
    def __control_receive(self):
        while True:
            msg, addr = self.control_sock.recvfrom(16384)
            opt = msg[0]
            ip_addr = addr[0]
            if opt == START:
                session_id = msg[1:]
                if (ip_addr, session_id) not in self.data_dict:
                    self.data_dict[(ip_addr, session_id)] = Window_buffer()
                self.control_send(msg)
            elif opt == STOP:
                self.data_dict[(ip_addr, session_id)] = self.data_dict[(ip_addr, session_id)].stop()
            elif opt == FASTER:
                pass
            elif opt == SLOWER:
                pass
            elif opt == CONFIG:
                sensor = cbor2.loads(msg[1:])
                self.sensor_list[sensor['id']] = sensor
            elif opt == DISCOVER:
                self.__discover()
            elif opt == MULTI:
                i = 1
                msg_list = []
                while i < len(msg):
                    size = msg[i]
                    i += 1
                    msg_list.append(msg[i: i + size])
                    i += size
        
    def start_receive(self):
        self.__receive_thread.start()
        self.__buffer_thread.start()
        self.__print_thread.start()
        self.__qos_thread.start()
        
    def __receive(self):
        while True:
            data, addr = self.sock.recvfrom(16384)
            ip_addr = addr[0]
            self.__queue.put((data, ip_addr))

            
    def __print(self):
        while True:
            time.sleep(1)
            print('\n----------------')
            print('total received:', self.count)
            print('queue size:', self.__queue.qsize())
            for k, v in self.data_dict.items():
                print(k, v.count, v.loss_rate())
                
    def __qos(self):
        while True:
            time.sleep(self.qos_freq)
            q_size = self.__queue.qsize()
            if q_size > self.qos_queue_upper:
                msg = b'0'
            elif q_size < self.qos_queue_lower:
                msg = b'1'
            for k in self.data_dict.keys():
                self.control_send(msg, k[0])
            
    def control_send(self, msg, ip_addr: str):
        self.control_sock.sendto(msg, (ip_addr, self.port + 1))
        
    def __buffer_window(self):
        
        while True:
            data, ip_addr = self.__queue.get()
            
            self.count += 1
            
            decoded_data = self.decode(data)
            
            id = decoded_data['id']
            
            if (ip_addr, id) not in self.data_dict:
                self.data_dict[(ip_addr, id)] = Window_buffer()
                
            self.data_dict[(ip_addr, id)].update(decoded_data)
        
    def decode(self, data):
        offset = 0
        v = int.from_bytes(data[offset : offset + len_v], 'big')
        offset += len_v
        
        id = int.from_bytes(data[offset: offset + len_id], 'big')
        offset += len_id
        
        # cc = int.from_bytes(data[offset: offset + len_cc], 'big')
        # offset += len_cc
        
        # pt = int.from_bytes(data[offset: offset + len_pt], 'big')
        # offset += len_pt
        
        csrc = int.from_bytes(data[offset: offset + len_csrc], 'big')
        offset += len_csrc
        
        ts = int.from_bytes(data[offset: offset + len_ts], 'big')
        offset += len_ts
        
        sn = int.from_bytes(data[offset: offset + len_sn], 'big')
        offset += len_sn
        
        
        payload = data[offset:]
        
        return {'v': v, 'id': id, 'csrc': csrc, 'sn': sn, 'ts': ts, 'payload': payload}
    
    
        
    
        