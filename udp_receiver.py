import socket
import time

def start_server(host='0.0.0.0', port=9924):
    # Create a socket object for UDP
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        # Bind the socket to the address and port
        s.bind((host, port))
        print("UDP Server is listening on", host, port)

        while True:
            print(s.recvfrom(4096))
        # start_time = time.time()
        # total_bytes = 0

        # try:
        #     while True:
        #         # Receive data from the client (1024 bytes buffer size)
        #         data, addr = s.recvfrom(4096)
        #         if not data:
        #             break
        #         # Update total bytes received
        #         total_bytes += len(data)

        #         # Calculate elapsed time
        #         current_time = time.time()
        #         elapsed_time = current_time - start_time

        #         if elapsed_time >= 1:  # Each second
        #             print(f'Bytes received per second from {addr}: {total_bytes / elapsed_time / 1024}')
        #             # Reset timer and byte count
        #             start_time = current_time
        #             total_bytes = 0
        # except KeyboardInterrupt:
        #     print("Server stopped manually.")
        # finally:
        #     print('Server shutdown.')

if __name__ == "__main__":
    start_server()
