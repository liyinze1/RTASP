import time
import random
from RTASP import *

class random_data(sensor):
    
    def __init__(self, id, packet_size=4096):
        self.id = id
        self.packet_size = packet_size
        self.active = False
        self.duration = 0.01
        
    def get_data(self):
        time.sleep(self.duration)
        return random.randbytes(self.packet_size)
    
    def fast(self):
        self.duration /= 2
        
    def slow(self):
        self.duration *= 2

sender = RTASP_sender(dest_ip='192.168.10.104', sender_ip='192.168.10.108', repeat_duration=1, repeat=3)
data = random_data(0)
sender.register(data)

# sender.send_info()

# sender.start(0)

# time.sleep(30)

# sender.stop(0)