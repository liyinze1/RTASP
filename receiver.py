import socket
import time

UDP_IP = "0.0.0.0"
UDP_PORT = 23000

sock = socket.socket(socket.AF_INET, # Internet
                     socket.SOCK_DGRAM) # UDP
sock.bind((UDP_IP, UDP_PORT))

t = 10

flag = True

sock.settimeout(5)

sock.setsockopt( 
        socket.SOL_SOCKET, 
        socket.SO_RCVBUF, 
        8192)

while True:
    # if time.time() > timeout:
    #     break
    # head, addr = sock.recvfrom(16)
    # t += head
    try:
        data, addr = sock.recvfrom(128)
        # print(type(data))
        # break
    except:
        break
    # if flag:
    #     flag = False
    #     timeout = time.time() + 10
    # print("received message: %s" % data)
    # break
    t += len(data)

print(t)