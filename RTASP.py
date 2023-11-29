from queue import Queue
import random
import socket
from threading import Thread, Condition
import time
import cbor2
from abc import ABC, abstractmethod

len_v = 1
len_cc = 1
len_pt = 1
len_csrc = 1
len_id = 2
len_ts = 2
len_sn = 2

STOP = int.to_bytes(0, 1)
START = int.to_bytes(1, 1)
SLOWER = int.to_bytes(2, 1)
FASTER = int.to_bytes(3, 1)
DISCOVER = int.to_bytes(4, 1)
SENSOR_INFO = int.to_bytes(5, 1)
CONFIG = int.to_bytes(6, 1)
MULTI = int.to_bytes(7, 1)
END = int.to_bytes(8, 1)

# window_size = 1000

# len_len = 2

class sensor(ABC):
    def __init__(self, id, packet_size, tp):
        self.id = id
        self.tp = tp
        self.packet_size = packet_size
        
    @abstractmethod
    def start(self):
        pass
    
    @abstractmethod
    def fast(self):
        pass
    
    @abstractmethod
    def slow(self):
        pass
    
    @abstractmethod
    def stop(self):
        pass
    
    @abstractmethod
    def get_data(self):
        return b''
    
    @abstractmethod
    def configure(self, data):
        pass
    
    def info(self):
        return self.__dict__

class udp_with_ack:
    
    '''
    |              ack header             |
    | 1bit ack | ------- 7bit sn ---------|
    '''

    def __init__(self, callback_receive, ip='0.0.0.0', port=23001, repeat=3, repeat_duration=1):
        self.control_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.control_sock.bind((ip, port))
        
        self.repeat = repeat
        self.repeat_duration = repeat_duration
        self.sn = 0
        self.callback_receive = callback_receive
        self.sending_dict = {}
        
        self.receive_thread = Thread(target=self.__receive)
        print('start listening', port, 'at', ip)
        self.receive_thread.start()
        
        self.condition = Condition()
        
    def __receive(self):
        while True:
            msg, addr = self.control_sock.recvfrom(4096)
            
            if msg[0] > 127: # get ack
                sn = msg[0] - 128
                if sn in self.sending_dict and self.sending_dict[sn] == addr:
                    self.condition.acquire()
                    self.sending_dict.pop(sn)
                    self.condition.notify()
                    self.condition.release()
                    
            else: # get control msg
                print('get', msg[1:], 'from', addr)
                self.control_sock.sendto(int.to_bytes(msg[0] + 128), addr) # send ack
                self.callback_receive(msg[1:], addr)
                
    def send(self, dest_addr, msg):
        
        print('sending', msg, 'to', dest_addr)
        
        payload = int.to_bytes(self.sn, 1) + msg
        self.sending_dict[self.sn] = dest_addr
        for i in range(self.repeat):
            self.control_sock.sendto(payload, dest_addr)
            self.condition.acquire()
            self.condition.wait_for(lambda: self.sn not in self.sending_dict, timeout=self.repeat_duration)
            self.condition.release()
            if self.sn not in self.sending_dict:
                self.sn += 1
                self.sn %= 128
                return 0
        
        self.sending_dict.pop(self.sn)
        self.sn += 1
        self.sn %= 128
        print('already tried %d times...timeout!'%self.repeat)
        return 1
    
class packet_sender:
    def __init__(self, version: int=0, dest_ip: str='127.0.0.1', dest_port: int=23000, sender_ip: str='127.0.0.1', sender_port: int=23000, session_id: int=None):
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
        self.sock.bind((sender_ip, sender_port))
        
        self.timestamp = 0
        self.__clock_thread = Thread(target=self.__clock)
        self.__clock_thread.start()
        
    def __clock(self):
        time.sleep(1)
        self.timestamp += 1
        
    def send(self, csrc: bytes, payload: bytes):
        # self.__transmit_queue.put((index, payload))
        self.sn %= 65536

        packet = self.v + self.id + csrc + self.timestamp.to_bytes(len_ts) + self.sn.to_bytes(len_sn, 'big') + payload
        self.sn += 1
        
        self.sock.sendto(packet, self.dest_addr)
        
        return packet
class RTASP_sender:
    def __init__(self, dest_ip: str='127.0.0.1', dest_port: int=23000, sender_ip: str='127.0.0.1', sender_port: int=23000):
        self.sensor_list = {}
        self.sensor_active = {}
        
        assert dest_port % 2 == 0
        
        self.dest_ip = dest_ip
        self.dest_port = dest_port
        self.dest_addr = (dest_ip, dest_port)
        self.dest_control_addr = (dest_ip, dest_port+1)
        
        self.control_socket = udp_with_ack(callback_receive=self.__control_msg_analysis, port=sender_port+1)
        
        self.session_id = random.randint(0, 65535).to_bytes(len_id, 'big')
        self.sender = packet_sender(dest_ip=dest_ip, dest_port=dest_port, sender_ip=sender_ip, sender_port=sender_port, session_id=self.session_id)
        
    def __control_msg_analysis(self, msg, addr):
        if addr == self.dest_control_addr:
            opt = msg[0:1]
            if opt == DISCOVER:
                self.send_info()
            elif opt == START:
                sensors_to_start = msg[1:]
                if len(sensors_to_start) == 0:
                    sensors_to_start = self.sensor_list.keys()
                else:
                    sensors_to_start = cbor2.loads(sensors_to_start)
                for id in sensors_to_start:
                    self.start(id)
            elif opt == STOP:
                sensors_to_stop = msg[1:]
                if len(sensors_to_stop) == 0:
                    sensors_to_stop = self.sensor_list.keys()
                else:
                    sensors_to_stop = cbor2.loads(sensors_to_stop)
                for id in sensors_to_stop:
                    self.stop(id)
    
    def register(self, sensor):
        self.sensor_list[sensor.id] = sensor
        self.sensor_active[sensor.id] = False

    def configure(self, data):
        data = data[1:]
        id = cbor2.loads(data)['id']
        self.sensor_list[id].configure(data)
        
    def send_info(self):
        sensor_info_list = {}
        for id, sensor in self.sensor_list.items():
            sensor_info_list[id] = sensor.info()
        return self.control_socket.send(self.dest_control_addr, SENSOR_INFO + cbor2.dumps(sensor_info_list))
        
    def start(self, sensor_id):
        self.sensor_active[sensor_id] = True
        self.sensor_list[sensor_id].start()
        Thread(target=self.__send_data, args=(sensor_id, )).start()
        
    def __send_data(self, sensor_id):
        print('sensor', sensor_id, 'start sending...')
        sensor = self.sensor_list[sensor_id]
        csrc = int.to_bytes(sensor_id, 1)
        while self.sensor_active[sensor_id]:
            self.sender.send(csrc, sensor.get_data())
    
    def stop(self, sensor_id):
        self.sensor_list[sensor_id].stop()
        self.sensor_active[sensor_id] = False
        
    def end(self):
        for sensor_id in self.sensor_list.keys():
            self.stop(sensor_id)
        self.control_socket.send(self.dest_control_addr, END + self.session_id)

class Window_buffer:
    def __init__(self, window_size: int=1000):
        self.window_size = window_size
        # self.window = [None] * window_size
        self.window = [None]
        self.offset = 0
        self.count = 0
        
        self.active = True
    
    def update(self, data):
        if not self.active:
            return
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
        self.active = False
        
    def start(self):
        self.active = True
        
    def end(self):
        return self.window

class RTASP_receiver:
    def __init__(self, ip: str='0.0.0.0', port: int=23000):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.port = port
        self.sock.bind((ip, port))
        
        self.control_sock = udp_with_ack(self.__control_msg_analysis, port=port+1)
        
        self.window_dict = {}
        self.data_dict = {}
        self.sensor_info_dict = {}
        
        self.count = 0
        
        self.qos_queue_upper = 10000
        self.qos_queue_lower = 1000
        
        # control channel
        self.control_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        self.__queue = Queue()
        
        Thread(target=self.__receive).start()
        Thread(target=self.__buffer_window).start()
        Thread(target=self.__print).start()
        
        
    def discover(self, addr):
        return_code = self.control_sock.send(addr, DISCOVER)
        if return_code != 0:
            print('Failed to connect to', addr)
        return return_code
    
    def start(self, addr, sensor_id=None):
        if addr not in self.sensor_info_dict:
            if self.discover() != 0:
                return
        if sensor_id == None:
            self.control_sock.send(addr, START)
        else:
            self.control_sock.send(addr, START+sensor_id)

    def __control_msg_analysis(self, msg, control_addr):
        addr = (control_addr[0], control_addr[1] - 1)
        opt = msg[0:1]
        if opt == SENSOR_INFO:
            self.sensor_info_dict[addr] = cbor2.loads(msg[1:])
        elif opt == START:
            if addr not in self.sensor_info_dict:
                self.discover()
        elif opt == END:
            session_id = int.from_bytes(msg[1:])
            self.data_dict[(addr, session_id)] = self.data_dict[(addr, session_id)].end()
            
    def __receive(self):
        while True:
            data, addr = self.sock.recvfrom(16384)
            self.__queue.put((data, addr))

    def __buffer_window(self):
        
        while True:
            data, addr = self.__queue.get()
            
            self.count += 1
            
            decoded_data = self.decode(data)
            
            id = decoded_data['id']
            
            if (addr, id) not in self.data_dict:
                self.data_dict[(addr, id)] = Window_buffer()
                # todo: ask for sensor info
                
            self.data_dict[(addr, id)].update(decoded_data)
            
    def __print(self):
        while True:
            time.sleep(1)
            print('\n----------------')
            print('total received:', self.count)
            print('queue size:', self.__queue.qsize())
            for k, v in self.data_dict.items():
                print(k, v.count, v.loss_rate())
            
            for key, window in self.data_dict.items():
                print('addr:', key[0], 'session id:', key[1], 'loss rate:', window.loss_rate())
        
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
    
    
        
    
        