'''
This is to test the latency of the RTASP running on the roadrunner, so there's just data channel without control channel
We use the max UDP packet, which is 65535B, and it's 65507B besiedes the headers of IP and UDP
The size of RTASP data channel header is 8B, so the max payload is 65499
'''

import random
import threading
import time
# from api import *
from serial import Serial
import socket


len_v = 1
len_cc = 1
len_pt = 1
len_csrc = 1
len_id = 2
len_ts = 2
len_sn = 2

class packet_sender:
    def __init__(self, version: int=0, dest_ip: str='127.0.0.1', dest_port: int=23000, sender_ip: str='127.0.0.1', sender_port: int=23000, serial_device='/dev/ttyS1', baud_rate=1000000, session_id: int=None):
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
        self.sock.setblocking(True)
        # self.sock.bind((sender_ip, sender_port))
        
        self.timestamp = 0
        self.__clock_alive = True
        self.__clock_thread = threading.Thread(target=self.__clock)
        self.__clock_thread.start()
        
        self.len_data = 0
        
        self.ser = Serial(serial_device, baud_rate)
        
    def __clock(self):
        while self.__clock_alive:
            time.sleep(1)
            self.timestamp += 1
            self.timestamp %= 65536
    
    def send_uart(self, csrc: bytes, payload: bytes):
        packet = self.v + self.session_id + csrc + self.timestamp.to_bytes(len_ts, 'big') + self.sn.to_bytes(len_sn, 'big') + payload
        self.sn += 1
        self.sn %= 65536
        self.ser.write(packet)
        
    def send(self, csrc: bytes, payload: bytes):
        packet = self.v + self.session_id + csrc + self.timestamp.to_bytes(len_ts, 'big') + self.sn.to_bytes(len_sn, 'big') + payload
        self.sn += 1
        self.sn %= 65536
        self.sock.sendto(packet, self.dest_addr)
        
    def end(self):
        self.sock.close()
        self.ser.close()
        self.__clock_alive = False
        self.__clock_thread.join()
        

def test_latency_ethernet(packet_size):
    sender = packet_sender(dest_ip='192.168.2.1')
    csrc = int.to_bytes(0, 1, 'big')

    dummy_data = random.randbytes(packet_size)

    t0 = time.time()
    for i in range(100):
        sender.send(csrc, dummy_data)
    t1 = time.time() - t0
    print('rtasp by ethernet', t1)
    sender.end()

    t0 = time.time()
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.setblocking(True)
    for i in range(100):
        udp_sock.sendto(dummy_data, ('192.168.2.1', 23000))
    t2 = time.time() - t0
    print('udp by ethernet', t2)
    udp_sock.close()

    return [t1, t2]

def test_latency_uart(packet_size, baud_rate):
    sender = packet_sender(dest_ip='192.168.2.1', baud_rate=baud_rate)
    csrc = int.to_bytes(0, 1, 'big')

    dummy_data = random.randbytes(packet_size)

    t0 = time.time()
    for i in range(100):
        sender.send_uart(csrc, dummy_data)
    t1 = time.time() - t0
    print('rtasp by uart', t1)
    
    sender.end()

    t0 = time.time()
    ser = Serial('/dev/ttyS1', baud_rate)
    for i in range(100):
        ser.write(dummy_data)
    t2 = time.time() - t0
    print('udp by uart', t2)
    ser.close()
    
    return [t1, t2]


packet_size_list = [64, 256, 1024, 4096, 16384, 65499]
baud_rate_list = [115200, 230400, 460800, 921600]


f = open('log.txt', 'w')

for packet_size in packet_size_list:
    f.write('------packet size--------' + str(packet_size) + '\n')
    # print('------packet size--------', packet_size)
    f.write(str(test_latency_ethernet(packet_size)) + '\n')
    
    for baud_rate in baud_rate_list:
        f.write('baud rate' + str(baud_rate) + '\n')
        f.write(str(test_latency_uart(packet_size, baud_rate)) + '\n')

f.close()