import subprocess
import shlex
import RTASP
from RTASP import *

class microphone(sensor):
    
    def __init__(self, id, packet_size, tp='microphone', sample_rate: int=48000, width: str='S32_LE', channels: int=4):
        self.id = id
        self.tp = tp
        self.sample_rate = sample_rate
        self.width = width
        self.channels = channels
        self.packet_size = packet_size
        
        
    def start(self):
        cmd = 'arecord -Dac108 -f %s -r %d -c %d'  % (self.width, self.sample_rate, self.channels)
        cmd = shlex.split(cmd)
        self.pipe = subprocess.Popen(cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            bufsize=self.packet_size * 10
                            )
        
    def get_data(self):
        return self.pipe.stdout.read(self.packet_size)
    
    def stop(self):
        return self.pipe.kill()

    def configure(self, data):
        if 'width' in data:
            self.width = data['width']
        if 'sample_rate' in data:
            self.sample_rate = data['sample_rate']
        if 'channels' in data:
            self.channels = data['channels']
            
            
mic = microphone(0, 2048)
print(mic.info())