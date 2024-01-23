import subprocess
import shlex
from RTASP import *

class audio_sensor(sensor):
    
    def __init__(self, id, packet_size=4096, tp='audio'):
        self.id = id
        self.tp = tp
        self.packet_size = packet_size
        
    def start(self):
        cmd = 'ffmpeg -re -i ../test.wav -acodec copy -'
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
    
    def stop(self):
        self.active = False
        self.pipe.kill()
        
audio = audio_sensor(0)

sender = RTASP_sender(dest_ip='10.147.19.97', sender_ip='10.147.19.221', repeat_duration=3, repeat=5)

sender.register(audio)

