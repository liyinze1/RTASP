import subprocess
import shlex
import RTASP

# initialize
packet_size = 16
controller = RTASP.RTSAP(0, 1, [0], [0])

# record
cmd = 'arecord -Dac108 -f S32_LE -r 48000 -c 4 -d 10'
cmd = shlex.split(cmd)
pipe = subprocess.Popen(cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    bufsize=packet_size * 10
                    )

# header
pipe.stdout.read(124)

while True:
    data = pipe.stdout.read(packet_size)
    if len(data) == 0:
        break
    controller.packet(0, data)
    
