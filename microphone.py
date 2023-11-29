from RTASP import sensor
import subprocess
import shlex

class microphone(sensor):
    
    def __init__(self, id, packet_size, tp='microphone', sample_rate: int=48000, width: str='S32_LE', channels: int=4):
        self.id = id
        self.tp = tp
        self.sample_rate = sample_rate
        self.width = width
        self.channels = channels
        self.packet_size = packet_size
        
        
    def start(self):
        cmd = 'arecord -Dac108 -f S32_LE -r 48000 -c 4'
        cmd = shlex.split(cmd)
        self.pipe = subprocess.Popen(cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            bufsize=self.packet_size * 10
                            )
        
    def get_data(self):
        return self.pipe.stdout.read(2048)
    
    def stop(self):
        return self.pipe.kill()
    
    
    
    