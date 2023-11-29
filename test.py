import socket
import time

# sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# sock.bind(('127.0.0.1', 23000))
# payload = b'Hallo'
# while True:
#     # sock.sendto(payload, ('172.27.92.252', 23000))
#     sock.sendto(payload, ('127.0.0.1', 23001))
#     time.sleep(1)
    
    
from threading import Thread
import time


import threading
import time

sign = True

def t(p):
    while sign:
        pass
    print(p)

def f():
    threading.Thread(target = t, args = ('123',)).start()
    
f()

time.sleep(4)
sign = False

# class A:
    
#     def __init__(self):
#         self.array = []
#         thread_a = Thread(target = self.a)
#         thread_b = Thread(target = self.b)
#         thread_b.start()
#         thread_a.start()
    
#     def a(self):
#         self.array.append('a')
#         print(self.array)
        
#     def b(self):
#         thread_c = Thread(target = self.c)
#         thread_c.start()
        
#     def c(self):
#         while True:
#             time.sleep(2)
#             print('count-----')
        
# a = A()
