# from api import *
import serial
import time
import random
from rtasp_low_power import uart_connection
    
uart = uart_connection()

dummy_data = random.randbytes(1024)

for i in range(1000):
    uart.send_data(dummy_data)

