import time
import random
from RTASP import *

class random_data(sensor):
    
    def __init__(self, id, packet_size=4096):
        self.id = id
        self.packet_size = packet_size
        self.active = False
        # self.duration = 0.001
        
    def get_data(self):
        # time.sleep(self.duration)
        return random.randbytes(self.packet_size)
    
    # def fast(self):
    #     self.duration /= 2
        
    # def slow(self):
    #     self.duration *= 2

sender = RTASP_sender(dest_ip='3.123.215.67', sender_ip='0.0.0.0', dest_port=9924, sender_port=9924, repeat_duration=1, repeat=3)
data = random_data(0)
sender.register(data)

sender.force_start(0)

# sender.send_info()

# sender.start(0)

# time.sleep(30)

# sender.stop(0)

# sender = packet_sender(dest_ip='3.123.215.67', sender_ip='0.0.0.0', dest_port=9924, sender_port=9924)
# csrc = int.to_bytes(0, 1, 'big')

# while True:
#     data = random.randbytes(4096)
#     sender.send(csrc, data)