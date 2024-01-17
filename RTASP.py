import random
import socket
import threading
import time
import cbor2
from abc import ABC, abstractmethod
from collections import deque

len_v = 1
len_cc = 1
len_pt = 1
len_csrc = 1
len_id = 2
len_ts = 2
len_sn = 2

STOP = int.to_bytes(0, 1, 'big')
START = int.to_bytes(1, 1, 'big')
SLOWER = int.to_bytes(2, 1, 'big')
FASTER = int.to_bytes(3, 1, 'big')
DISCOVER = int.to_bytes(4, 1, 'big')
SENSOR_INFO = int.to_bytes(5, 1, 'big')
CONFIG_SENSOR = int.to_bytes(6, 1, 'big')
MULTI = int.to_bytes(7, 1, 'big')
END = int.to_bytes(8, 1, 'big')
CONFIG = int.to_bytes(9, 1, 'big')

# window_size = 1000

# len_len = 2

class sensor(ABC):
    def __init__(self, id, packet_size, tp):
        self.id = id
        self.tp = tp
        self.packet_size = packet_size
        
    def start(self):
        pass
    
    def fast(self):
        pass
    
    def slow(self):
        pass
    
    def stop(self):
        pass
    
    @abstractmethod
    def get_data(self):
        return b''
    
    def configure(self, data):
        pass
    
    def sleep(self):
        pass
    
    def info(self):
        return self.__dict__

class udp_with_ack:
    
    '''
    |              ack header             |
    | 1bit ack | ------- 7bit sn ---------|
    '''

    def __init__(self, callback_receive, ip='0.0.0.0', port:int=23001, repeat:int=3, repeat_duration:int=1):
        self.control_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.control_sock.bind((ip, port))
        
        self.repeat = repeat
        self.repeat_duration = repeat_duration
        self.sn = 0
        self.callback_receive = callback_receive
        self.sending_dict = {}
        
        self.receive_thread = threading.Thread(target=self.__receive)
        print('start listening', port, 'at', ip)
        self.receive_thread.start()
        
        self.condition = threading.Condition()
        self.get_ack = False
        
    def __receive(self):
        while True:
            msg, addr = self.control_sock.recvfrom(4096)
            
            sn = int.from_bytes(msg[:2], 'big')
            
            if sn > 32767: # get ack
                sn -= 32768
                print('Get ACK from', addr, '\theader: ', sn)
                # self.get_ack = True
                if sn in self.sending_dict and self.sending_dict[sn] == addr:
                    self.condition.acquire()
                    self.sending_dict.pop(sn)
                    self.condition.notify()
                    self.condition.release()
                    
            else: # get control msg
                print('get', msg, 'from', addr, '\theader: ', sn)
                self.control_sock.sendto(int.to_bytes(msg[0] + 128, 1, 'big') + msg[1:2], addr) # send ack
                self.callback_receive(msg[2:], addr)
                
    def send(self, dest_addr, msg):
        send_thread = threading.Thread(target=self.__send, args=(dest_addr, msg))
        send_thread.start()
        # send_thread.join() # if I use join, then it won't get any ACK
    
    def __send(self, dest_addr, msg):
        
        print('sending', msg, 'to', dest_addr, ', waiting for ACK')
        
        if dest_addr[1] % 2 == 0:
            dest_addr = (dest_addr[0], dest_addr[1] + 1)    # control message must send to a even number sock

        payload = int.to_bytes(self.sn, 2, byteorder='big') + msg
        self.sending_dict[self.sn] = dest_addr
        for i in range(self.repeat):
            self.control_sock.sendto(payload, dest_addr)
            # print(threading.enumerate())
            # print('thread is active?', self.receive_thread.is_alive())
            self.condition.acquire()
            self.condition.wait_for(lambda: self.sn not in self.sending_dict, timeout=self.repeat_duration)
            self.condition.release()
            if self.sn not in self.sending_dict:
                self.sn += 1
                self.sn %= 32768
                self.get_ack = False
                return 0
        
        self.sending_dict.pop(self.sn)
        self.sn += 1
        self.sn %= 32768
        print('already tried %d times...timeout!'%self.repeat)
        return 1
    
class packet_sender:
    def __init__(self, version: int=0, dest_ip: str='127.0.0.1', dest_port: int=23000, sender_ip: str='127.0.0.1', sender_port: int=23000, session_id: int=None):
        assert dest_port % 2 == 0
        self.v = version.to_bytes(len_v, 'big') # 8 bit version number

        if session_id == None:
            self.session_id = random.randint(0, 65535).to_bytes(len_id, 'big') # random stream id
        else:
            self.session_id = session_id
        self.sn = 0
        
        self.dest_addr = (dest_ip, dest_port)
        self.dest_ip = dest_ip
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((sender_ip, sender_port))
        
        self.timestamp = 0
        self.__clock_thread = threading.Thread(target=self.__clock)
        self.__clock_thread.start()
        
    def __clock(self):
        while True:
            time.sleep(1)
            self.timestamp += 1
            self.timestamp %= 65536
        
    def send(self, csrc: bytes, payload: bytes):
        packet = self.v + self.session_id + csrc + self.timestamp.to_bytes(len_ts, 'big') + self.sn.to_bytes(len_sn, 'big') + payload
        self.sn += 1
        self.sn %= 65536
        
        self.sock.sendto(packet, self.dest_addr)
        
        return packet

class RTASP_sender:
    def __init__(self, dest_ip: str='127.0.0.1', dest_port: int=23000, sender_ip: str='127.0.0.1', sender_port: int=23000, configure_callback=None, repeat=3, repeat_duration=1):
        self.sensor_list = {}
        self.sensor_active = {}
        
        assert dest_port % 2 == 0
        
        self.dest_ip = dest_ip
        self.dest_port = dest_port
        self.dest_addr = (dest_ip, dest_port)
        self.dest_control_addr = (dest_ip, dest_port+1)
        
        self.control_socket = udp_with_ack(callback_receive=self.__control_msg_analysis, port=sender_port+1, repeat=repeat, repeat_duration=repeat_duration)
        
        self.session_id = random.randint(0, 65535).to_bytes(len_id, 'big')
        self.sender = packet_sender(dest_ip=dest_ip, dest_port=dest_port, sender_ip=sender_ip, sender_port=sender_port, session_id=self.session_id)
        
        self.configure_callback = configure_callback
        
    def __control_msg_analysis(self, msg, addr):
        if addr == self.dest_control_addr:
            opt = msg[0:1]
            if opt == DISCOVER:
                self.send_info()
            elif opt == START:
                if len(msg[1:]) == 0:  # start all sensors
                    for sensor_id in self.sensor_list.keys():
                        self.start(sensor_id)
                else:   # start specific sensor
                    self.start(msg[1])
            elif opt == STOP:
                if len(msg[1:]) == 0:  # stop all sensors
                    for sensor_id in self.sensor_list.keys():
                        self.stop(sensor_id)
                else:   # stop specific sensor
                    self.stop(msg[1])
            elif opt == CONFIG_SENSOR:
                sensor_id = msg[1]
                config = cbor2.loads(msg[2:])
                self.configure_sensor(sensor_id, config)
            elif opt == END:
                for sensor_id in self.sensor_list.keys():
                    self.stop(sensor_id)
    
    def register(self, sensor):
        self.sensor_list[sensor.id] = sensor
        self.sensor_active[sensor.id] = False

    def configure_sensor(self, sensor_id, data):
        '''
            Configure sensor
        '''
        self.sensor_list[sensor_id].configure(data)
        
    def send_info(self):
        '''
            Send all sensor info to the server
            must be called before start
        '''
        sensor_info_list = {}
        for id, sensor in self.sensor_list.items():
            sensor_info_list[id] = sensor.info()
        return self.control_socket.send(self.dest_control_addr, SENSOR_INFO + cbor2.dumps(sensor_info_list))
        
    def start(self, sensor_id):
        '''
            this method will call start() method of the sensor,
            and start an thread to pipe data
        '''
        self.sensor_active[sensor_id] = True
        self.sensor_list[sensor_id].start()
        threading.Thread(target=self.__send_data, args=(sensor_id, )).start()
        
    def __send_data(self, sensor_id):
        print('sensor', sensor_id, 'start sending...')
        sensor = self.sensor_list[sensor_id]
        csrc = int.to_bytes(sensor_id, 1, 'big')
        while self.sensor_active[sensor_id]:
            self.sender.send(csrc, sensor.get_data())
    
    def stop(self, sensor_id):
        '''
            this method will call stop() method of the sensor,
            and stop the thread of piping data
        '''
        self.sensor_list[sensor_id].stop()
        self.sensor_active[sensor_id] = False
        
    def end(self):
        '''
            this method will stop all sensors,
            and send END to the server
        '''
        for sensor_id in self.sensor_list.keys():
            self.stop(sensor_id)
        self.control_socket.send(self.dest_control_addr, END)

class Window_buffer:
    def __init__(self, window_size: int=1000):
        self.window_size = window_size
        # self.window = [None] * window_size
        self.window = deque([None] * window_size)

        self.count = 0
        
        self.left_sn = 0
        self.right_sn = window_size - 1
        
        self.buffer = deque()
        
        self.max_sn = 0
    
    # todo: sn overflow
    def update(self, data):
        sn = data['sn']
        if sn < self.left_sn:
            return
        elif sn > self.right_sn:
            offset = sn - self.right_sn
            for i in range(offset):
                v = self.window.popleft()
                if v is not None:
                    self.buffer.append(v) # pop left items to buffer
                self.window.append(None) # add None items to make it to window size
            self.left_sn += offset
            self.right_sn = sn
        
        self.count += 1
        self.max_sn = max(self.max_sn, sn)
        
        # self.window[sn - self.left_sn] = data
        
        try:
            self.window[sn - self.left_sn] = data
        except Exception as e:
            print(e)
            print('sn', sn, '\tleft_sn', self.left_sn, '\tlen_deque', len(self.window))
            
    def receive(self):
        while len(self.buffer) == 0:
            pass
        return self.buffer.popleft()
    
    def loss_rate(self):
        return 1 - self.count / (self.max_sn + 1)
        
    def end(self):
        while len(self.window) > 0:
            v = self.window.popleft()
            if v is not None:
                self.buffer.append(v)
        self.buffer.append(None)    # None means the end of the stream
        return self.buffer

class RTASP_receiver:
    def __init__(self, ip: str='0.0.0.0', port: int=23000, print=True):
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
        
        # list to receive data
        self.__queue = deque()
        
        threading.Thread(target=self.__receive).start()
        threading.Thread(target=self.__buffer_window).start()
        if print:
            threading.Thread(target=self.__print).start()
        
    def discover(self, addr):
        '''
            discover sensors at a specific (ip, sock)
            If connected successfully, a dict with sensor information will be returned
        '''
        self.control_sock.send(addr, DISCOVER)
        time.sleep(1)
        if addr in self.sensor_info_dict:
            return 0
        else:
            return 1
    
    def start(self, addr, sensor_id=None):
        '''
            start a sensor to generate data at a specific (ip, sock)
        '''
        if addr not in self.sensor_info_dict:
            print('no sensor at this address')
            return
        if sensor_id == None:
            self.control_sock.send(addr, START)
        else:
            self.control_sock.send(addr, START + sensor_id)
            
    def stop(self, addr, sensor_id=None):
        '''
            stop a sensor from generating data
        '''
        if sensor_id == None:
            self.control_sock.send(addr, STOP)
        else:
            self.control_sock.send(addr, STOP + sensor_id)
            
    def end(self, addr):
        '''
            the end of a session
            all sensors will stop
            on the server, the sliding window will also stop
        '''
        self.control_sock.send(addr, END)
        return self.sensor_info_dict.pop(addr), self.data_dict.pop(addr).end()
    
    def configure_sensor(self, addr, sensor_id, config):
        '''
            send a configuration dict to a specific sensor
        '''
        if type(sensor_id) == int:
            sensor_id = sensor_id.to_bytes(1, 'big')
        self.control_sock.send(addr, CONFIG_SENSOR + sensor_id + cbor2.dumps(config))
    
    def configure(self, addr, config):
        '''
            send a configuration dict to the sender
        '''
        self.control_sock.send(addr, CONFIG_SENSOR + cbor2.dumps(config))

    def __control_msg_analysis(self, msg, control_addr):
        addr = (control_addr[0], control_addr[1] - 1)
        opt = msg[0:1]
        if opt == SENSOR_INFO:
            # got the sensor info, ready to start
            self.sensor_info_dict[addr] = cbor2.loads(msg[1:])
            self.data_dict[addr] = Window_buffer()
        elif opt == END:
            self.data_dict[addr].end()
            
        # elif opt == START:
        #     if addr not in self.sensor_info_dict:
        #         self.discover()

    def __receive(self):
        while True:
            data, addr = self.sock.recvfrom(16384)
            self.__queue.append((data, addr))

    def __buffer_window(self):
        
        while True:
            while len(self.__queue) == 0:
                pass
            data, addr = self.__queue.popleft()

            self.count += 1
            
            decoded_data = self.decode(data)
            
            if addr in self.data_dict:
                # if data is not in sensor list, drop
                self.data_dict[addr].update(decoded_data)
            
    def __print(self):
        while True:
            time.sleep(1)
            if len(self.data_dict) > 0:
                print('\n----------------')
                print('total received:', self.count)
                print('queue size:', len(self.__queue))

                for addr, window in self.data_dict.items():
                    print('addr:', addr, 'packet received:', window.count, 'loss rate:', window.loss_rate())
            
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
    