import subprocess
import shlex
# init command


cmd = 'arecord -Dac108 -f S32_LE -r 48000 -c 4 -d 10'
cmd = shlex.split(cmd)

# excute ffmpeg command
pipe = subprocess.Popen(cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    # bufsize=1000
                    )


# header
s = pipe.stdout.read(124)

n = 0

while pipe.poll() is None:
    frame = pipe.stdout.read(160)
    n += 1
    
print(n)