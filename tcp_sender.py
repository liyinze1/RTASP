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
        start_time = time.time()
        total_bytes = 0
        while True:
            data = random.randbytes(4096)
            s.sendall(data)
            # time.sleep(0.001)
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

