from RTASP import *
import time

receiver = RTASP_receiver('0.0.0.0')
receiver.start_receive()

# while True:
#     time.sleep(1)
#     for addr in receiver.data_dict.keys():
#         print(addr, len(receiver.data_dict[addr]))
