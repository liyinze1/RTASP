from rtasp_low_power import *
import socket
import subprocess
import shlex
from api import *
import time

ratios = ['0.1', '0.2', '0.3', '0.7']

for i in range(4):
    print(i, ':', ratios[i])
    
ratio = ratios[int(input('Please enter a number to select a ratio: '))]   

class aac_sensor(sensor):
    def __init__(self, id, packet_size=None, tp='aac'):
        self.id = id
        self.tp = tp
        self.packet_size = packet_size
    
    def start(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('127.0.0.1', 23000))
        self.audio_process = subprocess.Popen(shlex.split('/usr/bin/ffmpeg -re -i /home/acme/rtasp-low-power/roadrunner/audio/wav.wav -acodec aac -q:a %s -f adts udp://127.0.0.1:23000'%ratio))
        
    def stop(self):
        self.sock.close()
        self.audio_process.kill()
    
    def get_data(self):
        data, addr = self.sock.recvfrom(1024)
        return data
    
sensor_obj = aac_sensor(1)
uart = uart_connection()
sender = RTASP_sender(uart_sock=uart)
sender.register(sensor_obj)
sender.send_info()

time.sleep(20)
suspend_to_ram(30)

