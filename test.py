import subprocess
import shlex
# init command


cmd = 'arecord -Dac108 -f S32_LE -r 48000 -c 4 -d 10'
cmd = shlex.split(cmd)

size_list = [4, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096, 7680, 15360]

for size in size_list:

    # excute ffmpeg command
    pipe = subprocess.Popen(cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        # bufsize=1000
                        )


    # header
    s = pipe.stdout.read(124)

    count = 0

    s = bytes(0)

    while True:
        frame = pipe.stdout.read(size)
        if len(frame) == 0:
            break
        else:
            count += 1

    print('------------------')
    print(size)
    print(count * size)
    print((count * size) / 7680000)