import socket
import random
import time

def send_random_data(host='3.123.215.67', port=9924):
    # Create a socket object for UDP
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            while True:
                # Generate random data
                
                s.sendto(random.randbytes(4096), (host, port))

                # Wait for 2 seconds before sending next data
                time.sleep(0.001)
        except KeyboardInterrupt:
            print("Stopped by user.")

if __name__ == "__main__":
    send_random_data()
