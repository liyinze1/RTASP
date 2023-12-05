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

# initialize
packet_size = RTASP.len_payload
sender = RTASP.RTSAP_sender(0, 1, [0], [0], '0.0.0.0', 23000)
# sender = RTASP.RTSAP_sender(0, 1, [0], [0], '192.168.0.217', 23000)
duration = 10

# record
cmd = 'arecord -Dac108 -f S32_LE -r 48000 -c 4 -d %d' % (duration)
cmd = shlex.split(cmd)
pipe = subprocess.Popen(cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    # bufsize=packet_size * 10
                    )

# header
pipe.stdout.read(RTASP.len_payload)

count = 0

# while True:
while True:
    data = pipe.stdout.read(packet_size)
    
    if len(data) == 0: # or pipe.poll() is not None:
        break
    count += len(sender.send(0, data))

# print((count * packet_size) / 768000 / duration)

print(count)
# print(sender.count)