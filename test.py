import subprocess
import numpy as np
import shlex

# init command
cmd = "ffmpeg -i test.wav -acodec copy |"

# excute ffmpeg command
pipe = subprocess.run(cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=True
                    )

# debug
print(pipe.stdout)
