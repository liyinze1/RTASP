from RTASP import *
import time
import random

sender = RTASP_sender(dest_ip='172.27.92.252')
f = 1/5000

for i in range(10000):
    time.sleep(random.random() * 0.01)
    # time.sleep(f)
    sender.send(0, b'fjaohiuehfsnf;heiuhkjewiufhewuhiuhru32he230r0regioroihgh02r023jr2joidhwoi')