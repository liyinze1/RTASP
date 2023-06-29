import subprocess
import shlex
import RTASP

# initialize
packet_size = 128
# sender = RTASP.RTSAP_sender(0, 1, [0], [0], '172.27.92.252', 23000)
sender = RTASP.RTSAP_sender(0, 1, [0], [0], '127.0.0.1', 23000)
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
pipe.stdout.read(124)

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