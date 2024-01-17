import time
import random
from RTASP import *

class random_data(sensor):
    
    def __init__(self, id, packet_size=4096):
        self.id = id
        self.packet_size = packet_size
        self.active = False
        
        
    def get_data(self):
        time.sleep(0.1)
        return random.randbytes(self.packet_size)

sender = RTASP_sender(dest_ip='10.147.19.97', sender_ip='10.147.19.232', repeat_duration=1, repeat=3)
data = random_data(0)
sender.register(data)

sender.send_info()

sender.start(0)

time.sleep(5)

sender.stop(0)