import random
import socket
import threading
import time
import cbor2
from abc import ABC, abstractmethod
from collections import deque


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

# window_size = 1000

# len_len = 2

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
    
    def sleep(self):
        pass
    
    def info(self):
        return self.__dict__

class udp_with_ack:
    def __init__(self, callback_receive=None, local_address=('0.0.0.0', 9925), remote_address=None, timeout=2, max_retries=3):
        self.callback_receive = callback_receive
        self.local_address = local_address
        self.remote_address = remote_address
        self.timeout = timeout
        self.max_retries = max_retries
        
        self.version = int.to_bytes(0, 1, 'big')
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(local_address)
        # self.sock.settimeout(timeout)
        self.running = True
        self.ack_received = threading.Event()
        self.sn = 0
        self.expected_ack_sn = -1
        
        self.receive_thread = threading.Thread(target=self._receive_message)
        self.receive_thread.start()

    def send(self, message:bytes, remote_address=None):
        if remote_address is None:
            remote_address = self.remote_address
            if remote_address is None:
                print('Please specify a remote address')
                return 0
        if remote_address[1] % 2 == 0:
            remote_address = (remote_address[0], remote_address[1] + 1)
        
        self.sn += 1
        self.sn %= 32768
        self.expected_ack_sn = self.sn
        packet = self.version + int.to_bytes(self.sn, 2, byteorder='big') + message
        
        for _ in range(self.max_retries):
            try:
                print('Sending message', packet, ' to', remote_address)
                self.sock.sendto(packet, remote_address)
                self.ack_received.wait(timeout=self.timeout)
                if self.ack_received.is_set() and self.expected_ack_sn is None:
                    print("Correct ACK received")
                    return 0
                else:
                    print("Timeout or incorrect ACK, resending message")
                    self.ack_received.clear()
            except socket.timeout:
                print("Timeout, resending message")
        return 1

    def _receive_message(self):
        while self.running:
            try:
                data, address = self.sock.recvfrom(1024)
                sn = int.from_bytes(data[1:3], 'big')
                if sn > 32767:
                    sn -= 32768
                    print('Received sn:', sn, '\t expected:', self.expected_ack_sn)
                    if sn == self.expected_ack_sn:
                        self.expected_ack_sn = None
                        self.ack_received.set()
                else:
                    if sn <= self.sn:
                        print('old message, drop it')
                    self.sn = sn
                    sn += 32768
                    self.sock.sendto(self.version + sn.to_bytes(2, 'big'), address)
                    print(f"Sent ACK with SN: {sn - 32768} to {address}")
                    if self.callback_receive is not None:
                        self.callback_receive(data[3:], address)
            except socket.timeout:
                print("Timeout...")


    def stop(self):
        self.running = False
        self.sock.close()
    
class packet_sender:
    def __init__(self, version: int=0, dest_ip: str='127.0.0.1', dest_port: int=9924, sender_ip: str='127.0.0.1', sender_port: int=9924, session_id: int=None):
        assert dest_port % 2 == 0
        self.v = version.to_bytes(len_v, 'big') # 8 bit version number

        if session_id == None:
            self.session_id = random.randint(0, 65535).to_bytes(len_id, 'big') # random stream id
        else:
            self.session_id = session_id
        self.sn = 0
        
        self.dest_addr = (dest_ip, dest_port)
        self.dest_ip = dest_ip
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((sender_ip, sender_port))
        
        self.timestamp = 0
        self.__clock_thread = threading.Thread(target=self.__clock)
        self.__clock_thread.start()
        
        self.len_data = 0
        
    def __print(self):
        if self.len_data != 0:
            print('Send data to', self.dest_addr, '\tdata rate:', self.len_data / 1024, 'KB', end='\r')
            self.len_data = 0
        
        
    def __clock(self):
        while True:
            time.sleep(1)
            self.timestamp += 1
            self.timestamp %= 65536
            self.__print()
        
    def send(self, csrc: bytes, payload: bytes):
        packet = self.v + self.session_id + csrc + self.timestamp.to_bytes(len_ts, 'big') + self.sn.to_bytes(len_sn, 'big') + payload
        self.sn += 1
        self.sn %= 65536
        
        self.len_data += self.sock.sendto(packet, self.dest_addr)
        
        return packet

class RTASP_sender:
    def __init__(self, dest_ip: str='127.0.0.1', dest_port: int=9924, sender_ip: str='127.0.0.1', sender_port: int=9924, configure_callback=None, timeout=2, max_retries=3):
        self.sensor_list = {}
        self.sensor_active = {}
        
        # check address and port
        assert dest_port % 2 == 0
        self.dest_ip = dest_ip
        self.dest_port = dest_port
        self.dest_addr = (dest_ip, dest_port)
        self.dest_control_addr = (dest_ip, dest_port+1)
        
        # control channel
        self.control_socket = udp_with_ack(callback_receive=self.__control_msg_analysis, remote_address=self.dest_control_addr, timeout=timeout, max_retries=max_retries)
        
        # data channel
        self.session_id = random.randint(0, 65535).to_bytes(len_id, 'big')
        self.sender = packet_sender(dest_ip=dest_ip, dest_port=dest_port, sender_ip=sender_ip, sender_port=sender_port, session_id=self.session_id)
        
        self.configure_callback = configure_callback
        
    def __control_msg_analysis(self, msg, addr):
        if addr == self.dest_control_addr:
            opt = msg[0:1]
            if opt == DISCOVER:
                self.send_info()
            elif opt == START:
                if len(msg[1:]) == 0:  # start all sensors
                    for sensor_id in self.sensor_list.keys():
                        self.start(sensor_id)
                else:   # start specific sensor
                    self.start(msg[1])
            elif opt == STOP:
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
    
    def register(self, sensor):
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

class Window_buffer:
    def __init__(self, window_size: int=1000):
        self.window_size = window_size
        
        # self.window = [None] * window_size
        self.window = deque([None] * window_size)

        self.count = 0
        
        self.left_sn = 0
        self.right_sn = window_size - 1
        
        self.buffer = deque()
        
        self.max_sn = 0
        
        self.active = True
    
    # todo: sn overflow
    def update(self, data):
        if not self.active:
            return
        sn = data['sn']
        if sn < self.left_sn:
            return # old data, drop
        elif sn > self.right_sn:
            offset = sn - self.right_sn
            for i in range(offset):
                self.window.append(None) # add None items to make it to window size
                
                # try:
                #     v = self.window.popleft()
                # except Exception as e:
                #     print(e)
                #     print('len', len(self.window))
                #     print('sn', sn, 'left_sn', self.left_sn, 'right_sn', self.right_sn)
                    
                v = self.window.popleft()
                # v = self.window.pop(0)
                
                if v is not None:
                    self.buffer.append(v) # pop left items to buffer
            
            self.left_sn += offset
            self.right_sn = sn
            
        
        self.count += 1
        self.max_sn = max(self.max_sn, sn)
    
        # if len(self.window) != 1000:
        #     print('sn', sn, '\tleft_sn', self.left_sn, '\tlen_deque', len(self.window))
        #     print(self.window)
        #     return
            
        self.window[sn - self.left_sn] = data
    
    def receive(self):
        while len(self.buffer) == 0:
            pass
        return self.buffer.popleft()
    
    def loss_rate(self):
        return 1 - self.count / (self.max_sn + 1)
        
    def end(self):
        self.active = False
        while len(self.window) > 0:
            v = self.window.popleft()
            # v = self.window.pop(0)
            if v is not None:
                self.buffer.append(v)
        # self.buffer.append(None)    # None means the end of the stream
        return self.buffer

class RTASP_receiver:
    def __init__(self, ip: str='0.0.0.0', port: int=9924, print=True, timeout=2, max_retries=3):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.port = port
        self.sock.bind((ip, port))
        
        self.control_sock = udp_with_ack(callback_receive=self.__control_msg_analysis, local_address=(ip, port+1), timeout=timeout, max_retries=max_retries)
        
        self.window_dict = {}
        self.data_dict = {}
        self.sensor_info_dict = {}
        
        self.count = 0
        
        self.qos_queue_upper = 10000
        self.qos_queue_lower = 1000
        
        # list to receive data
        self.__queue = deque()
        
        self.len_data = 0
        
        threading.Thread(target=self.__receive).start()
        threading.Thread(target=self.__buffer_window).start()
        if print:
            threading.Thread(target=self.__print).start()
        
    def discover(self, addr):
        '''
            discover sensors at a specific (ip, sock)
            If connected successfully, a dict with sensor information will be returned
        '''
        self.control_sock.send(DISCOVER, addr)
        time.sleep(1)
        if addr in self.sensor_info_dict:
            return 0
        else:
            return 1
    
    def start(self, addr, sensor_id=None):
        '''
            start a sensor to generate data at a specific (ip, sock)
        '''
        if addr not in self.sensor_info_dict:
            print('no sensor at this address')
            return
        if sensor_id == None:
            self.control_sock.send(START, addr)
        else:
            self.control_sock.send(START + sensor_id, addr)
            
    def fast(self, addr, sensor_id=None):
        if sensor_id == None:
            self.control_sock.send(FASTER, addr)
        else:
            self.control_sock.send(FASTER + sensor_id, addr)
            
    def slow(self, addr, sensor_id=None):
        if sensor_id == None:
            self.control_sock.send(SLOWER, addr)
        else:
            self.control_sock.send(SLOWER + sensor_id, addr)
            
    def sleep(self, addr, sensor_id=None):
        if sensor_id == None:
            self.control_sock.send(SLEEP, addr)
        else:
            self.control_sock.send(SLEEP + sensor_id, addr)
            
    def stop(self, addr, sensor_id=None):
        '''
            stop a sensor from generating data
        '''
        if sensor_id == None:
            self.control_sock.send(STOP, addr)
        else:
            self.control_sock.send(STOP + sensor_id, addr)
            
    def end(self, addr):
        '''
            the end of a session
            all sensors will stop
            on the server, the sliding window will also stop
        '''
        self.control_sock.send(END, addr)
        return self.sensor_info_dict.pop(addr), self.data_dict.pop(addr).end()
    
    def configure_sensor(self, addr, sensor_id, config):
        '''
            send a configuration dict to a specific sensor
        '''
        if type(sensor_id) == int:
            sensor_id = sensor_id.to_bytes(1, 'big')
        self.control_sock.send(CONFIG_SENSOR + sensor_id + cbor2.dumps(config), addr)
    
    def configure(self, addr, config):
        '''
            send a configuration dict to the sender
        '''
        self.control_sock.send(CONFIG_SENSOR + cbor2.dumps(config), addr)
        
    def sleep(self, addr, timeout):
        '''
            sleep for some seconds
        '''
        self.control_sock.send(SLEEP + cbor2.dumps(timeout), addr)

    def __control_msg_analysis(self, msg, control_addr):
        addr = (control_addr[0], control_addr[1] - 1)
        opt = msg[0:1]
        if opt == SENSOR_INFO:
            # got the sensor info, ready to start
            self.sensor_info_dict[addr] = cbor2.loads(msg[1:])
            self.data_dict[addr] = Window_buffer()
        elif opt == END:
            self.data_dict[addr].end()
            
        # elif opt == START:
        #     if addr not in self.sensor_info_dict:
        #         self.discover()

    def __receive(self):
        while True:
            data, addr = self.sock.recvfrom(16384)
            
            self.len_data += len(data)
            
            self.__queue.append((data, addr))

    def __buffer_window(self):
        
        while True:
            while len(self.__queue) == 0:
                pass
            data, addr = self.__queue.popleft()

            self.count += 1
            
            decoded_data = self.decode(data)
            
            if addr in self.data_dict:
                # if data is not in sensor list, drop
                self.data_dict[addr].update(decoded_data)
            
    def __print(self):
        while True:
            time.sleep(1)
            if len(self.data_dict) > 0:
                # print('\n----------------')
                # print('total received:', self.count)
                # print('queue size:', len(self.__queue))
                if self.len_data > 1024:
                    print('data rate:', self.len_data / 1024, 'KB', end=' ')
                else:
                    print('data rate:', self.len_data, 'B', end=' ')
                    
                self.len_data = 0
                
                for addr, window in self.data_dict.items():
                    print('------- addr:', addr, '\tpacket received:', window.count, '\tloss rate:', window.loss_rate(), ' -------', end='\r')
            
    def decode(self, data):
        offset = 0
        v = int.from_bytes(data[offset : offset + len_v], 'big')
        offset += len_v
        
        id = int.from_bytes(data[offset: offset + len_id], 'big')
        offset += len_id
        
        # cc = int.from_bytes(data[offset: offset + len_cc], 'big')
        # offset += len_cc
        
        # pt = int.from_bytes(data[offset: offset + len_pt], 'big')
        # offset += len_pt
        
        csrc = int.from_bytes(data[offset: offset + len_csrc], 'big')
        offset += len_csrc
        
        ts = int.from_bytes(data[offset: offset + len_ts], 'big')
        offset += len_ts
        
        sn = int.from_bytes(data[offset: offset + len_sn], 'big')
        offset += len_sn
        
        payload = data[offset:]
        
        return {'v': v, 'id': id, 'csrc': csrc, 'sn': sn, 'ts': ts, 'payload': payload}
    
