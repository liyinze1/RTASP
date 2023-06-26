import random

class RTSAP:
    def __init__(self, version: int, cc: int, payload_types: list, csrc: list):
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
            self.timestamps.append(0) # 32 bit time stamp
            
        self.id = random.randint(0, 65535).to_bytes(2, 'big') # random stream id
            
        self.sn = 0
        
    def packet(self, index: int, payload: bytes):
        self.sn %= 65536
        self.timestamps[index] %= 65536
            
        packet = self.v + self.id + self.cc + self.payload_types[index] + self.sn.to_bytes(2, 'big') + self.timestamps[index].to_bytes(2, 'big') + payload
        self.sn += 1
        self.timestamps[index] += 1
        return packet
    
