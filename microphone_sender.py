import subprocess
import shlex
from RTASP import *

class microphone(sensor):
    
    def __init__(self, id, packet_size=4096, tp='microphone', sample_rate: int=48000, width: str='S32_LE', channels: int=4):
        self.id = id
        self.tp = tp
        self.sample_rate = sample_rate
        self.width = width
        self.channels = channels
        self.packet_size = packet_size
        self.active = False
        
        
    def start(self):
        cmd = 'arecord -Dac108 -f %s -r %d -c %d'  % (self.width, self.sample_rate, self.channels)
        cmd = shlex.split(cmd)
        self.pipe = subprocess.Popen(cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            bufsize=self.packet_size * 10
                            )
        self.active = True
        
    def get_data(self):
        while not self.active:
            pass
        return self.pipe.stdout.read(self.packet_size)
    
    def slow(self):
        self.stop()
        self.width = 'S16_LE'
        self.sample_rate = 16000
        self.start()
        
    def fast(self):
        self.stop()
        self.width = 'S32_LE'
        self.sample_rate = 48000
        self.start()
    
    def stop(self):
        self.active = False
        self.pipe.kill()

sender = RTASP_sender(dest_ip='10.147.19.97', sender_ip='10.147.19.221', repeat_duration=3, repeat=5)
mic = microphone(0)
sender.register(mic)

# sender.send_info()

# sender.start(0)

# time.sleep(10)

# mic.slow()

# time.sleep(10)

# sender.stop(0)

# sender.end()