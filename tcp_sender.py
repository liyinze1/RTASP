import socket
import random
import time


host='3.123.215.67'
port=9924
# Create a socket object
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    # Connect to the server
    s.connect((host, port))

    # Send data repeatedly
    try:
        while True:
            data = random.randbytes(4096)
            s.sendall(data)
            time.sleep(0.001)
    except KeyboardInterrupt:
        print("Stopped by user.")

