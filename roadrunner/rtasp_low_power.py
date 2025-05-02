import random
import threading
import time
from mpio import GPIO, DevMem
from serial import Serial
import socket
from abc import ABC, abstractmethod
import cbor2
import os

len_v = 1
len_cc = 1
len_pt = 1
len_csrc = 1
len_id = 2
len_ts = 2
len_sn = 2

STOP = int.to_bytes(0, 1, 'big')
START = int.to_bytes(1, 1, 'big')
SLOWER = int.to_bytes(2, 1, 'big')
FASTER = int.to_bytes(3, 1, 'big')
DISCOVER = int.to_bytes(4, 1, 'big')
SENSOR_INFO = int.to_bytes(5, 1, 'big')
CONFIG_SENSOR = int.to_bytes(6, 1, 'big')
MULTI = int.to_bytes(7, 1, 'big')
END = int.to_bytes(8, 1, 'big')
CONFIG = int.to_bytes(9, 1, 'big')
SLEEP = int.to_bytes(10, 1, 'big')
WAKE = int.to_bytes(11, 1, 'big')

class sensor(ABC):
    def __init__(self, id, packet_size, tp):
        self.id = id
        self.tp = tp
        self.packet_size = packet_size
        
    def start(self):
        pass
    
    def fast(self):
        pass
    
    def slow(self):
        pass
    
    def stop(self):
        pass
    
    @abstractmethod
    def get_data(self):
        return b''
    
    def configure(self, data):
        pass
    
    def sleep(self, timeout):
        pass
    
    def info(self):
        return self.__dict__
    
class uart_connection:
    def __init__(self, uart='/dev/ttyS1', baudrate=230400, dest_addr=('3.123.215.67', 9924), callback_receive=print, timeout=0.1):
        self.uart = Serial(uart, baudrate)
        
        ack = b'N'
        while ack == b'N':
            time.sleep(1)
            self.uart.write(b'?')
            ack = self.uart.read(1)
        print('got signal')
        
        network_msg = 'E4' + '.'.join([n.zfill(3) for n in dest_addr[0].split('.')]) + ':' + str(dest_addr[1]).zfill(5) + ':' + str(dest_addr[1] + 1).zfill(5)
        self.uart.write(network_msg.encode('ascii'))
        time.sleep(0.1)
        print(self.uart.read(self.uart.in_waiting))
        print('set up complete')
        
        self.callback_receive = callback_receive
        self.receive_thread = threading.Thread(target=self.receive)
        self.receive_thread.start()
        self.ack_received = threading.Event()
        self.timeout = timeout
        
        self.out_line = GPIO(1, GPIO.OUT, initial=GPIO.LOW)
        self.in_line = GPIO(2, GPIO.IN)
        self.wake_up_monitor_thread = threading.Thread(target=self.wake_up_monitor)
        self.wake_up_monitor_thread.start()
        
    def network_ready(self):
        self.uart.write(b'?')
                
    def send_data(self, data:bytes):
        return self._send(b'S' + int.to_bytes(len(data), 2, 'big') + data)

    def send_control(self, data:bytes):
        return self._send(b'C' + int.to_bytes(len(data), 2, 'big') + data)
        
    def _send(self, data):
        self.uart.write(data)
        if self.ack_received.wait(timeout=self.timeout):
            self.ack_received.clear()
            return True
        else:
            print('Timeout waiting for ack')
            return False
        
    def wake_up_monitor(self):
        while True:
            time.sleep(0.1)
            if self.in_line.get() is GPIO.HIGH:
                self.uart.write(b'R')
    
    def set_callback(self, callback_receive):
        self.callback_receive = callback_receive
        
    def receive(self):
        while True:
            c = self.uart.read(1)
            print('uart get', c)
            if c == b'A':
                self.ack_received.set()
            elif c == b'N':
                print('Unexpected uart error')
            elif c == b'C':
                length = int.from_bytes(self.uart.read(2), 'big')
                data = self.uart.read(length)
                self.callback_receive(data)
                print('got control channel message, length:', length) #, '\tdata:', data)

class udp_with_ack_uart:
    def __init__(self, uart: uart_connection, callback_receive=print, timeout=2, max_retries=3, version=0):
        self.callback_receive = callback_receive

        self.timeout = timeout
        self.max_retries = max_retries
        
        self.version = int.to_bytes(version, 1, 'big')
        self.sock = uart
        self.sock.set_callback(self.receive_message)
        self.running = True
        self.ack_received = threading.Event()
        self.sn = 0
        self.expected_ack_sn = -1

    def send(self, message:bytes):
        
        self.sn += 1
        self.sn %= 32768
        self.expected_ack_sn = self.sn
        packet = self.version + int.to_bytes(self.sn, 2, byteorder='big') + message
        for _ in range(self.max_retries):
            try:
                print('Sending message:', packet)
                self.sock.send_control(packet)
                self.ack_received.wait(timeout=self.timeout)
                if self.ack_received.is_set() and self.expected_ack_sn is None:
                    print("Correct ACK received")
                    self.ack_received.clear()
                    return 0
                else:
                    print("Timeout or incorrect ACK, resending message")
                    self.ack_received.clear()
            except socket.timeout:
                print("Timeout, resending message")
        return 1

    def receive_message(self, data):
        sn = int.from_bytes(data[1:3], 'big')
        if sn > 32767:
            # get ACK
            sn -= 32768
            print('Received sn:', sn, '\t expected:', self.expected_ack_sn)
            if sn == self.expected_ack_sn:
                self.expected_ack_sn = None
                self.ack_received.set()
        else:
            # get control message
            if sn <= self.sn:
                print('old message, drop it')
            self.sn = sn
            sn += 32768
            self.sock.send_control(self.version + sn.to_bytes(2, 'big'))
            print('Sent ACK with SN', sn - 32768)
            self.callback_receive(data[3:])

class packet_sender:
    def __init__(self, uart_sock: uart_connection, version: int=0, session_id: int=None):
        if session_id == None:
            self.session_id = random.randint(0, 65535).to_bytes(len_id, 'big') # random stream id
        else:
            self.session_id = session_id
        self.sn = 0
        self.v = version.to_bytes(1, 'big')
        
        self.uart_sock = uart_sock
        
        self.timestamp = 0
        self.__clock_alive = True
        self.__clock_thread = threading.Thread(target=self.__clock)
        self.__clock_thread.start()
        
        self.len_data = 0
        
    def __clock(self):
        while self.__clock_alive:
            time.sleep(1)
            self.timestamp += 1
            self.timestamp %= 65536
    
    def send(self, csrc: bytes, payload: bytes):
        packet = self.v + self.session_id + csrc + self.timestamp.to_bytes(len_ts, 'big') + self.sn.to_bytes(len_sn, 'big') + payload
        self.sn += 1
        self.sn %= 65536
        self.uart_sock.send_data(packet)
        
    def send_udp(self, payload: bytes):
        self.uart_sock.send_data(payload)
        
    def end(self):
        self.__clock_alive = False
        self.__clock_thread.join()
        
class RTASP_sender:
    def __init__(self, uart_sock: uart_connection, configure_callback=None, timeout=2, max_retries=3):
        self.sensor_list = {}
        self.sensor_active = {}
        
        # control channel
        self.control_socket = udp_with_ack_uart(uart=uart_sock, callback_receive=self.__control_msg_analysis, timeout=timeout, max_retries=max_retries)
        
        # data channel
        self.sender = packet_sender(uart_sock=uart_sock)
        self.configure_callback = configure_callback
        
    def __control_msg_analysis(self, msg):
        opt = msg[0:1]
        if opt == DISCOVER:
            self.send_info()
        elif opt == START:
            print('control channel: start')
            if len(msg[1:]) == 0:  # start all sensors
                for sensor_id in self.sensor_list.keys():
                    self.start(sensor_id)
            else:   # start specific sensor
                self.start(msg[1])
        elif opt == STOP:
            print('control channel: stop')
            if len(msg[1:]) == 0:  # stop all sensors
                for sensor_id in self.sensor_list.keys():
                    self.stop(sensor_id)
            else:   # stop specific sensor
                self.stop(msg[1])
        elif opt == CONFIG_SENSOR:
            sensor_id = msg[1]
            config = cbor2.loads(msg[2:])
            self.configure_sensor(sensor_id, config)
        elif opt == END:
            for sensor_id in self.sensor_list.keys():
                self.stop(sensor_id)
        elif opt == FASTER:
            if len(msg[1:]) == 0:  # faster all sensors
                for sensor_id in self.sensor_list.keys():
                    self.fast(sensor_id)
            else:   # faster specific sensor
                self.fast(msg[1])
        elif opt == SLOWER:
            if len(msg[1:]) == 0:  # slower all sensors
                for sensor_id in self.sensor_list.keys():
                    self.slow(sensor_id)
            else:   # slower specific sensor
                self.slow(msg[1])
        elif opt == SLEEP:
            print('control channel: sleep')
            timeout = cbor2.loads(msg[1:])
            DevMem.write_reg(0xFC040018, 0x300)
            os.system(f"sudo rtcwake -m mem -s {timeout}")
            # os.system(f"sudo rtcwake -m standby -s {timeout}")
        else:
            print('error! unknown option')
    
    def register(self, sensor: sensor):
        self.sensor_list[sensor.id] = sensor
        self.sensor_active[sensor.id] = False

    def configure_sensor(self, sensor_id, data):
        '''
            Configure sensor
        '''
        self.sensor_list[sensor_id].configure(data)
        
    def send_info(self):
        '''
            Send all sensor info to the server
            must be called before start
        '''
        sensor_info_list = {}
        for id, sensor in self.sensor_list.items():
            sensor_info_list[id] = sensor.info()
        return self.control_socket.send(SENSOR_INFO + cbor2.dumps(sensor_info_list))
        
    def start(self, sensor_id):
        '''
            this method will call start() method of the sensor,
            and start an thread to pipe data
        '''
        self.sensor_active[sensor_id] = True
        self.sensor_list[sensor_id].start()
        threading.Thread(target=self.__send_data, args=(sensor_id, )).start()
        
    def force_start(self, sensor_id):
        self.sensor_active[sensor_id] = True
        threading.Thread(target=self.__send_data, args=(sensor_id, )).start()
        
    def __send_data(self, sensor_id):
        print('sensor', sensor_id, 'start sending...')
        sensor = self.sensor_list[sensor_id]
        csrc = int.to_bytes(sensor_id, 1, 'big')
        while self.sensor_active[sensor_id]:
            self.sender.send(csrc, sensor.get_data())
        print('sensor', sensor_id, ' deactivate')
    
    def stop(self, sensor_id):
        '''
            this method will call stop() method of the sensor,
            and stop the thread of piping data
        '''
        self.sensor_active[sensor_id] = False
        self.sensor_list[sensor_id].stop()
        
    def end(self):
        '''
            this method will stop all sensors,
            and send END to the server
        '''
        for sensor_id in self.sensor_list.keys():
            self.stop(sensor_id)
        self.control_socket.send(END)
        
    def fast(self, sensor_id):
        self.sensor_list[sensor_id].fast()
        
    def slow(self, sensor_id):
        self.sensor_list[sensor_id].slow()



######## testing ########

def test_speed_helper():
    packet_size = int(input('packet_size:'))
    interval = float(input('interval:'))
    test_speed(packet_size, interval)
def test_speed(length: int=64, interval: float=0):
    con = uart_connection()
    data = random.randbytes(length)
    if interval == 0:
        while True:
            con.send_data(data)
    else:
        while True:
            time.sleep(interval)
            con.send_data(data)

def control_test():
    def print_data(data):
        print(data)
    uart = uart_connection()
    control_channel = udp_with_ack_uart(uart, callback_receive=print_data)
    while True:
        control_channel.send(input().encode('ascii'))
        
def throughput_test(length: int=1024):
    con = uart_connection()
    sender = packet_sender(uart_sock=con)
    while True:
        sender.send_udp(random.randbytes(length))
        
def sensor_test():
    class random_sensor(sensor):
        def __init__(self, id, packet_size, tp):
            self.id = id
            self.tp = tp
            self.packet_size = packet_size
            
        def get_data(self):
            return random.randbytes(self.packet_size)
        
    sensor_obj = random_sensor(1, 1024, 'random')
    uart = uart_connection()
    sender = RTASP_sender(uart_sock=uart)
    sender.register(sensor_obj)
    sender.send_info()
    
def latency_test(con:uart_connection, length=64, repeat=1000):
    data = random.randbytes(length)
    latency_list = []
    for _ in range(repeat):
        t0 = time.perf_counter()
        if con.send_data(data):
            t1 = time.perf_counter()
            latency_list.append((t1 - t0) * 1000)
            time.sleep(0.2)

    print('packet length:', length)
    print('average latency:', sum(latency_list) / len(latency_list))
    print('max latency:', max(latency_list),'min latency:', min(latency_list))
    print('loss rate:', 1 - len(latency_list) / repeat)
    
def latency_test_helper():
    con = uart_connection(timeout=0.3)
    while True:
        length = int(input('packet size:'))
        latency_test(con, length)
        

packet_dict = {}            
rtt_list = []
    
if __name__ == '__main__':
    # control_test()
    # throughput_test()
    # sensor_test()
    # latency_test_helper()
    # rtt_jitter_test()
    test_speed_helper()
    pass