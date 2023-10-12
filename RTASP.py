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


# window_size = 1000

# len_len = 2

class RTCASP_cmd:
    STOP = 0
    START = 1
    SLOWER = 2
    FASTER = 3
    DISCOVER = 4
    CONFIG = 5
    MULTI = 6
    

class RTCASP_sender:
    def __init__(self, dest_ip: str='127.0.0.1', port: int=23000):
        self.sensor_list = {}
        assert port % 2 == 0
        
        self.dest_ip = dest_ip
        self.dest_port = port
        
        self.control_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.control_sock.bind(('0.0.0.0', port + 1))
        
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
        if opt == RTCASP_cmd.START:
            self.start_transmit = True
        elif opt == RTCASP_cmd.STOP:
            self.stop_transmit = False
        elif opt == RTCASP_cmd.FASTER:
            pass
        elif opt == RTCASP_cmd.SLOWER:
            pass
        elif opt == RTCASP_cmd.CONFIG:
            sensor = cbor2.loads(msg[1:])
            self.sensor_list[sensor['id']] = sensor
        elif opt == RTCASP_cmd.DISCOVER:
            reply = bytes()
            for sensor in self.sensor_list.values():
                encoded_sensor = cbor2.dumps(sensor)
                reply += int.to_bytes(len(encoded_sensor), 'big') + encoded_sensor
        elif opt == RTCASP_cmd.MULTI:
            i = 1
            msg_list = []
            while i < len(msg):
                size = msg[i]
                i += 1
                msg_list.append(msg[i: i + size])
                i += size
        
    def control_send(self, msg):
        self.control_sock.sendto(msg, (self.dest_ip, self.dest_port))
        
    def register(self, id, type, reservation, sample_rate, power_comsumption):
        sensor = {'id': id, 'tp': type, 'rsv': reservation, 'sr': sample_rate, 'pwr': power_comsumption}
        self.sensor_list[id] = sensor
    
    def configure(self, id, type, reservation, sample_rate, power_comsumption):
        self.sensor_list[id] = {'id': id, 'tp': type, 'rsv': reservation, 'sr': sample_rate, 'pwr': power_comsumption}
        
    
        

class RTASP_sender:
    def __init__(self, version: int=0, cc: int=1, payload_types: list=[0], csrc: list=[0], dest_ip: str='127.0.0.1', dest_port: int=23000):
        assert cc == len(payload_types) == len(csrc)
        assert dest_port % 2 == 0
        self.v = version.to_bytes(len_v, 'big') # 8 bit version number
        self.cc = cc.to_bytes(len_cc, 'big') # 8 bit cc
        
        self.payload_types = []
        for pt in payload_types:
            self.payload_types.append(pt.to_bytes(len_pt, 'big')) # 8 bit payload type
            
        self.csrc = []
        self.timestamps = []
        for c in csrc:
            self.csrc.append(c.to_bytes(len_csrc, 'big')) # 8 bit csrc
            self.timestamps.append(0) # 16 bit time stamp
            
        self.id = random.randint(0, 65535).to_bytes(len_id, 'big') # random stream id
        
        self.sn = 0
        
        self.dest_addr = (dest_ip, dest_port)
        self.dest_ip = dest_ip
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('0.0.0.0', dest_port + 1))
        self.count = 0
        
        self.__transmit_duration = 1e-3
        
        # self.__transmit_queue = Queue()
        # self.transmit_thread = Thread(target=self.__transmit)
        # self.transmit_thread.start()
        
        self.__control_thread = Thread(target=self.__control_channel)
        self.__control_thread.start()
        
        self.control_msg_list = []
        
    def send(self, index: int, payload: bytes):
        # self.__transmit_queue.put((index, payload))
        time.sleep(self.__transmit_duration)
        self.sn %= 65536
        self.timestamps[index] %= 65536
        
        # len_packet = len_header + len(payload)
        # self.count += len_packet
        
        packet = self.v + self.id + self.cc + self.payload_types[index] + self.sn.to_bytes(len_sn, 'big') + self.csrc[index] + self.timestamps[index].to_bytes(len_ts, 'big') + payload
        self.sn += 1
        self.timestamps[index] += 1
        
        self.sock.sendto(packet, self.dest_addr)
        
        return packet
        
    # def __transmit(self):
    #     while True:
    #         index, payload = self.__transmit_queue.get()
    #         time.sleep(self.__transmit_duration)
    #         self.sn %= 65536
    #         self.timestamps[index] %= 65536
            
    #         # len_packet = len_header + len(payload)
    #         # self.count += len_packet
            
    #         packet = self.v + self.id + self.cc + self.payload_types[index] + self.sn.to_bytes(len_sn, 'big') + self.csrc[index] + self.timestamps[index].to_bytes(len_ts, 'big') + payload
    #         self.sn += 1
    #         self.timestamps[index] += 1
            
    #         self.sock.sendto(packet, self.dest_addr)
            
    

                        
    def __control_msg_analysis(self, msg):
        if msg == b'0':
            # slow down transmission
            self.__transmit_duration *= 2
        elif msg == b'1':
            # faster
            self.__transmit_duration = max(self.__transmit_duration, 1e-4)
        else:
            self.control_msg_list.append(msg)
        print('transmit duration', self.__transmit_duration)
    
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
        # if self.offset <= sn < self.offset + self.window_size:
        #     self.window[sn - self.offset] = data
        #     return []
        # elif sn >= self.offset + self.window_size:
        #     new_offset = sn - (self.offset + self.window_size) + 1
        #     out = self.window[:new_offset]
        #     self.window = self.window[new_offset:] + [None] * new_offset
        #     self.offset += new_offset
        #     self.window[sn - self.offset] = data
        #     return out
        # else:
        #     return None
        if sn >= len(self.window):
            self.window += [None] * (sn - len(self.window))
            self.window.append(data)
        else:
            self.window[sn] = data
    
    def loss_rate(self):
        return 1 - self.count / len(self.window)
        
    def clear(self):
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
        
        
        
    def start_receive(self):
        self.__receive_thread.start()
        self.__buffer_thread.start()
        self.__print_thread.start()
        self.__qos_thread.start()
        
    def __receive(self):
        while True:
            data, addr = self.sock.recvfrom(16384)
            self.__queue.put((data, addr))
            
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
        if type(msg) == bytes:
            size = len(msg).to_bytes(1, 'big')
            self.control_sock.sendto(size + msg, (ip_addr, self.port + 1))
        elif type(msg) == iter:
            buffer = b''
            for message in msg:
                buffer += len(message).to_bytes(1, 'big')
                buffer += message
            self.control_sock.sendto(buffer, (ip_addr, self.port + 1))
        
    def __buffer_window(self):
        
        while True:
            data, addr = self.__queue.get()
            
            ip_addr = addr[0]
            
            self.count += 1
            
            decoded_data = self.decode(data)
            
            id = decoded_data['id']
            
            if (ip_addr, id) not in self.data_dict:
                self.data_dict[(ip_addr, id)] = Window_buffer()
                
            self.data_dict[(ip_addr, id)].update(decoded_data)
            

            # window_output = self.data_dict[addr]['window'].update(decoded_data)
            # if window_output is not None:
            #     self.data_dict[addr]['data'] += window_output
        
        
        # while True:
        #     offset = 0
        #     while offset + len_packet < len(self.raw_data):
        #         decoded_data = self.decode(self.raw_data[offset: offset + len_packet])
        #         offset += len_packet
                
        #         id = decoded_data['id']
        #         if id not in self.window_dict:
        #             self.window_dict[id] = Window_buffer()
        #             self.data_dict[id] = {}
                
        #         window_out = self.window_dict[id].update(decoded_data)
        #         for data in window_out:
        #             if data is not None:
        #                 id = data['id']
        #                 csrc = data['csrc']
        #                 if csrc in self.data_dict[id]:
        #                     self.data_dict[id][csrc]['payload'].append(data('payload'))
        #                 else:
        #                     self.data_dict[id][csrc] = {'cc'}
                        
                    

        #     self.mutex.acquire()
        #     self.raw_data = self.raw_data[offset:]
        #     self.mutex.release()
        
    def decode(self, data):
        offset = 0
        v = int.from_bytes(data[offset : offset + len_v], 'big')
        offset += len_v
        
        id = int.from_bytes(data[offset: offset + len_id], 'big')
        offset += len_id
        
        cc = int.from_bytes(data[offset: offset + len_cc], 'big')
        offset += len_cc
        
        pt = int.from_bytes(data[offset: offset + len_pt], 'big')
        offset += len_pt
        
        sn = int.from_bytes(data[offset: offset + len_sn], 'big')
        offset += len_sn
        
        csrc = int.from_bytes(data[offset: offset + len_csrc], 'big')
        offset += len_csrc
        
        ts = int.from_bytes(data[offset: offset + len_ts], 'big')
        offset += len_ts
        
        payload = data[offset:]
        
        return {'v': v, 'id': id, 'cc': cc, 'pt': pt, 'csrc': csrc, 'sn': sn, 'ts': ts, 'payload': payload}
    
    
        
    
        