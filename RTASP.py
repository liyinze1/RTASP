import random
import socket

len_v = 1
len_cc = 1
len_pt = 1
len_csrc = 1
len_id = 2
len_ts = 2
len_sn = 2

len_header = len_v + len_cc + len_pt + len_csrc + len_id + len_ts + len_sn

len_len = 2

class RTSAP_sender:
    def __init__(self, version: int, cc: int, payload_types: list, csrc: list, dest_ip: str, dest_port: int):
        assert cc == len(payload_types) == len(csrc)
        self.v = version.to_bytes(1, 'big') # 8 bit version number
        self.cc = cc.to_bytes(1, 'big') # 8 bit cc
        
        self.payload_types = []
        for pt in payload_types:
            self.payload_types.append(pt.to_bytes(1, 'big')) # 8 bit payload type
            
        self.csrc = []
        self.timestamps = []
        for c in csrc:
            self.csrc.append(c.to_bytes(1, 'big')) # 8 bit csrc
            self.timestamps.append(0) # 16 bit time stamp
            
        self.id = random.randint(0, 65535).to_bytes(2, 'big') # random stream id
        
        self.sn = 0
        
        self.dest_addr = (dest_ip, dest_port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        self.count = 0
        
    def send(self, index: int, payload: bytes):
        self.sn %= 65536
        self.timestamps[index] %= 65536
        
        len_packet = len_header + len(payload)
        self.count += len_packet
        
        packet = self.v + self.id + self.cc + self.payload_types[index] + self.sn.to_bytes(2, 'big') + self.timestamps[index].to_bytes(2, 'big') + payload
        self.sn += 1
        self.timestamps[index] += 1
        
        self.sock.sendto(packet, self.dest_addr)
        
        return packet
    

class RTASP_receiver:
    def __init__(self, ip: str='0.0.0.0', port: int=23000):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((ip, port))
        self.data = {}
        
    def receive(self):
        data, addr = self.sock.recvfrom(2)
        len_packet = int.from_bytes(data, 'big')
        data, addr = self.sock.recvfrom(len_packet)
        
