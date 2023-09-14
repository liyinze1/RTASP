from RTASP import *
import time
import random

sender = RTASP_sender(dest_ip='172.27.92.252')

while True:
    time.sleep(random.random() * 0.1)
    sender.send(0, b'fjaohiuehfsnf;heiuhkjewiufhewuhiuhru32he230r0regioroihgh02r023jr2joidhwoi')