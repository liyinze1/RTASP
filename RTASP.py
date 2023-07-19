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

len_payload = 124

len_packet = len_header + len_payload

window_size = 1000

# len_len = 2

class RTSAP_sender:
    def __init__(self, version: int, cc: int, payload_types: list, csrc: list, dest_ip: str, dest_port: int):
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
        
        packet = self.v + self.id + self.cc + self.payload_types[index] + self.sn.to_bytes(len_sn, 'big') + self.csrc[index].to_bytes(len_csrc, 'big') + self.timestamps[index].to_bytes(len_ts, 'big') + payload
        self.sn += 1
        self.timestamps[index] += 1
        
        self.sock.sendto(packet, self.dest_addr)
        
        return packet
    

class RTASP_receiver:
    def __init__(self, ip: str='0.0.0.0', port: int=23000, timeout=10):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((ip, port))
        self.data_dict = {}
        
    def receive(self):
        try:
            while True:
                data, addr = self.sock.recvfrom(4096)
                
                offset = 0
                while offset < len(data) - len_packet:
                    decoded_data = self.decode(data[offset: offset + len_packet])
                    offset += len_packet
                
                # print(type(data))
                # break
        except:
            pass
        
    
    def buffer_window(self, decoded_data):
        id = decoded_data['id']
        if id not in self.data_dict:
            self.data_dict[decoded_data['id']] = {}

        id_dict = self.data_dict[decoded_data['id']]
        csrc = decoded_data['csrc']
        if csrc not in id_dict:
            source_dict = {}
            
            f = open(str(id) + '_' + str(csrc), 'wb')
            source_dict['f'] = f
            
            

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
        
        payload = data[offset: offset + len_payload]
        
        return {'v': v, 'id': id, 'cc': cc, 'pt': pt, 'csrc': csrc, 'sn': sn, 'ts': ts, 'payload': payload}
    
    
        

        
        
