from RTASP import udp_with_ack
import time

def callback(msg, addr):
    print(msg, addr)

server1 = udp_with_ack(callback_receive=callback, port=23000)

server2 = udp_with_ack(callback_receive=callback, port=24000)

server1.send(('127.0.0.1', 24000), b'hello from 1')

server2.send(('127.0.0.1', 23000), b'hello from 2')

time.sleep(2)