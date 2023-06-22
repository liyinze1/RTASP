import numpy as np
import socket

def decode_rtp(packet_bytes):
    ##Example Usage:
    #packet_bytes = '8008d4340000303c0b12671ad5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5'
    #rtp_params = DecodeRTPpacket(packet_bytes)
    #Returns dict of variables from packet (packet_vars{})
    packet_vars = {}
    byte1 = packet_bytes[0:2]           #Byte1 as Hex
    byte1 = int(byte1, 16)              #Convert to Int
    byte1 = format(byte1, 'b')          #Convert to Binary
    packet_vars['V'] = int(byte1[0:2], 2)     #Get RTP Version
    packet_vars['P'] = int(byte1[2:3])        #Get padding bit
    packet_vars['X'] = int(byte1[3:4])        #Get extension bit
    CC = int(byte1[4:8], 2)     #Get csi count
    packet_vars['CC'] = CC

    byte2 = packet_bytes[2:4]

    byte2 = int(byte2, 16)
    byte2 = format(byte2, 'b').zfill(8)
    packet_vars['M'] = int(byte2[0:1])  # Marker
    packet_vars['PT'] = int(byte2[1:8], 2) # payload type

    packet_vars['SN'] = int(str(packet_bytes[4:8]), 16) # sequence number

    packet_vars['T'] = int(str(packet_bytes[8:16]), 16) # timestamp

    packet_vars['SSRC'] = int(str(packet_bytes[16:24]), 16) # Synchronization source identifier
    
    if CC > 0:
        packet_vars['CSRC'] = int(str(packet_bytes[24:24 + 2 * CC]), 16)
        

    packet_vars['data'] = str(packet_bytes[24:])
    return packet_vars

def rtp_recv_server(ip='127.0.0.1', port='23000'):
    print("Selected Port is: " + str(port))
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
    sock.bind(('0.0.0.0', 1447))


# packet_bytes = '8008d4340000303c0b12671ad5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5d5'
# rtp_params = DecodeRTPpacket(packet_bytes)