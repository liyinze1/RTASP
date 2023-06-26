import subprocess
import shlex
# init command


cmd = "arecord -Dac108 -f S32_LE -r 48000 -c 4 -d 1"
cmd = shlex.split(cmd)

# excute ffmpeg command
pipe = subprocess.Popen(cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    # bufsize=1000
                    )


# print(pipe.stderr)
s = pipe.stdout.read()
print(type(s))
print(len(s))
