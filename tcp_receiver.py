# import socket
# import time

# def start_server(host='0.0.0.0', port=9924):
#     # Create a socket object
#     with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
#         # Bind the socket to the address and port
#         s.bind((host, port))
#         # Enable the server to accept connections
#         s.listen()
#         print("Server is listening on", host, port)

#         # Wait for a connection
#         conn, addr = s.accept()
#         with conn:
#             print('Connected by', addr)
#             start_time = time.time()
#             total_bytes = 0
#             try:
#                 while True:
#                     # Receive data from the client
#                     data = conn.recv(1024)
#                     if not data:
#                         break
#                     # Update total bytes received
#                     total_bytes += len(data)

#                     # Calculate elapsed time
#                     current_time = time.time()
#                     elapsed_time = current_time - start_time

#                     if elapsed_time >= 1:  # Each second
#                         print(f'Bytes received per second: {total_bytes / elapsed_time}')
#                         # Reset timer and byte count
#                         start_time = current_time
#                         total_bytes = 0
#             except KeyboardInterrupt:
#                 print("Server stopped manually.")
#             finally:
#                 print('Connection closed.')

# if __name__ == "__main__":
#     start_server()

import socket
import time
import threading

class bandwidth_calculator(object):
    def __init__(self,):
        self.count = 0
        self.print_thread = threading.Thread(target=self.print_band)
        self.print_thread.start()
        
    def update(self, c):
        self.count += c
        
    def print_band(self):
        time.sleep(1)
        print(self.count, end='\r')
        self.count = 0
        

host='0.0.0.0'
port=9924
calculator = bandwidth_calculator()
# Create a socket object
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    # Bind the socket to the address and port
    s.bind((host, port))
    # Enable the server to accept connections
    s.listen()
    print("Server is listening on", host, port)

    # Wait for a connection
    conn, addr = s.accept()
    with conn:
        print('Connected by', addr)
        
        while True:
            data = conn.recv(4096)
            calculator.update(len(data))
            
            

                
