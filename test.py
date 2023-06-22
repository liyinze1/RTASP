import subprocess
import numpy as np
import shlex

# init command
cmd = "arecord -Dac108 -f S32_LE -r 48000 -c 4"

# excute ffmpeg command
pipe = subprocess.run(cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=True
                    )

# debug
print(pipe.stdout)
