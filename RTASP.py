import random
import socket
from threading import Thread
from queue import Queue
import time

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

class RTASP_sender:
    def __init__(self, version: int=0, cc: int=1, payload_types: list=[0], csrc: list=[0], dest_ip: str='127.0.0.1', dest_port: int=23000):
        assert cc == len(payload_types) == len(csrc)
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
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        self.count = 0
        
    def send(self, index: int, payload: bytes):
        self.sn %= 65536
        self.timestamps[index] %= 65536
        
        # len_packet = len_header + len(payload)
        # self.count += len_packet
        
        packet = self.v + self.id + self.cc + self.payload_types[index] + self.sn.to_bytes(len_sn, 'big') + self.csrc[index] + self.timestamps[index].to_bytes(len_ts, 'big') + payload
        self.sn += 1
        self.timestamps[index] += 1
        
        self.sock.sendto(packet, self.dest_addr)
        
        return packet
    
class Window_buffer:
    def __init__(self, window_size: int=1000):
        self.window_size = window_size
        # self.window = [None] * window_size
        self.window = []
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
        self.sock.bind((ip, port))
        self.window_dict = {}
        self.data_dict = {}
        
        self.count = 0
        
        self.qos_freq = 1 / 10
        self.qos_queue_upper = 10000
        self.qos_queue_lower = 1000
        
        self.__receive_thread = Thread(target=self.__receive)
        self.__buffer_thread = Thread(target=self.__buffer_window)
        self.__print_thread = Thread(target=self.__print)
        self.__qos_thread = Thread(target=self.__qos)
        
        self.__queue = Queue()
        
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
                print(k, len(v.count), v.loss_rate())
                
    def __qos(self):
        while True:
            time.sleep(self.qos_freq)
            q_size = self.__queue.qsize()
            if q_size > self.qos_queue_upper:
                pass
            elif q_size < self.qos_queue_lower:
                pass
            
            
        
    def __buffer_window(self):
        
        while True:
            data, addr = self.__queue.get()
            
            ip_addr = addr[0]
            
            self.count += 1
            
            decoded_data = self.decode(data)
            
            id = decoded_data['id']
            
            if (ip_addr, id) not in self.data_dict:
                self.data_dict[(addr, id)] = Window_buffer()
                
            

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
    
    
class RTCASP_sender:
    def __init__(self,):
        pass
    
    def initialize(self, cc: dict, pt: dict, ip: str='127.0.0.1'):
        pass
    
        
    
        