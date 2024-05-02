import socket
import random
import time

def send_random_data(host='3.123.215.67', port=9924):
    # Create a socket object for UDP
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            
            start_time = time.time()
            total_bytes = 0
            
            while True:
                # Generate random data
                
                data = random.randbytes(512)
                
                s.sendto(data, (host, port))

                # Wait for 2 seconds before sending next data
                
                total_bytes += len(data)

                # Calculate elapsed time
                current_time = time.time()
                elapsed_time = current_time - start_time

                if elapsed_time >= 1:  # Each second
                    print(total_bytes / elapsed_time / 1024)
                    # Reset timer and byte count
                    start_time = current_time
                    total_bytes = 0
                # time.sleep(0.001)
        except KeyboardInterrupt:
            print("Stopped by user.")

if __name__ == "__main__":
    send_random_data()
