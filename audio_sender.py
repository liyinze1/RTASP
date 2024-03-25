import subprocess
import shlex
from RTASP import *

class audio_sensor(sensor):
    
    def __init__(self, id, packet_size=4096, tp='audio'):
        self.id = id
        self.tp = tp
        self.packet_size = packet_size
        
    def start(self):
        self.f = open('../test.wav', 'rb')
        
    def get_data(self):
        time.sleep(1/187)
        return self.f.read(self.packet_size)
        
audio = audio_sensor(0)

sender = RTASP_sender(dest_ip='192.168.10.104', sender_ip='192.168.10.108', repeat_duration=3, repeat=5)

sender.register(audio)

