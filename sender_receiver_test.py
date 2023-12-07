import RTASP
import random
import time
class random_sensor(RTASP.sensor):
    
    def __init__(self, id, packet_size, tp):
        super().__init__(id, packet_size, tp)
        self.description = 'test'
        self.duration = 0.01
        
    def get_data(self):
        time.sleep(self.duration)
        return random.randbytes(self.packet_size)
    
    def start(self):
        pass
    
    def configure(self, data):
        pass
    
    def fast(self):
        pass
    
    def stop(self):
        pass
    
    def slow(self):
        pass
    
    def sleep(self):
        pass
    
sensor = random_sensor(0, 512, 0)
rtasp_sender = RTASP.RTASP_sender(dest_ip='127.0.0.1', dest_port=25000)
rtasp_sender.register(sensor)

rtasp_receiver = RTASP.RTASP_receiver(port=25000)

# time.sleep(1)

rtasp_sender.send_info()

time.sleep(0.1)
print(rtasp_receiver.sensor_info_dict)

rtasp_sender.start(0)

time.sleep(3)

rtasp_sender.stop(0)

time.sleep(3)

rtasp_receiver.start(('127.0.0.1', 23000))

time.sleep(3)

rtasp_receiver.end(('127.0.0.1', 23000))



