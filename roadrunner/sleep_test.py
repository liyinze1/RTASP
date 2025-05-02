# from api import *
import time
import os
from mpio import GPIO, DevMem

def standby(seconds: int):
    """Go into active standby and wake up after a set time"""

    os.system(f"sudo rtcwake -m standby -s {seconds}")
    
def suspend_to_ram(seconds: int):
    """Suspend to RAM and wake up after a set time"""

    DevMem.write_reg(0xFC040018, 0x300)
    os.system(f"sudo rtcwake -m mem -s {seconds}")

f = open('out.txt', 'w')

for _ in range(3):
    time.sleep(1)
    f.write('running\n') 
    
standby(5)

for _ in range(5):
    time.sleep(1)
    f.write('stand by\n') 
    
suspend_to_ram(5)
for _ in range(5):
    time.sleep(1)
    f.write('suspend\n') 

for _ in range(3):
    time.sleep(1)
    f.write('running\n') 