from RTASP import *
import time

receiver = RTASP_receiver(print=True)

while len(receiver.sensor_info_dict) == 0:
    pass

print(receiver.sensor_info_dict)
sensor_addr = list(receiver.sensor_info_dict.keys())[0]

time.sleep(1)

receiver.start(sensor_addr)

time.sleep(170)
# time.sleep(30)

receiver.stop(sensor_addr)

sensor_info, data_dict = receiver.end(sensor_addr)

# f = open('aac.aac', 'wb')
# for data in data_dict:
#     f.write(data['payload'])
# f.close()

# receiver.sleep(sensor_addr, 30)

# print('start sensor')
# time.sleep(5)
# receiver.stop(sensor_addr)
# print('stop sensor')

# receiver.sleep(sensor_addr, 5)
# print('sleep 5 seconds')

# time.sleep(10)

# receiver.start(sensor_addr)
# print('start sensor')
# time.sleep(5)
# receiver.stop(sensor_addr)
# print('stop sensor')

