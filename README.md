# RTASP-low-power

## Message formats to UART->Cell gateway

### Query network status:

'?'

UART->Cell gateway will send an ack 'A' if it has established an LTE-M or NB-IoT connection, or a nack 'N' if it is yet to do so

### Establish IPv4 connection:

'E4NNN.NNN.NNN.NNN:SSSSS:CCCCC'

Establish IPv4 UDP Connection to NNN.NNN.NNN.NNN with stream port SSSSS and control port CCCCC.

### Send control message:

'C' (uint16_t payload length)  ...payload...

First byte is 'C' char, immediately followed by 16 bit unsigned integer representing the length in bytes of the payload (not the full UART message length!), then the payload.

### Send stream data:

'S' (uint16_t payload length)  ...payload...

First byte is 'S' char, immediately followed by 16 bit unsigned integer representing the length in bytes of the payload (not the full UART message length!), then the payload.

### Ready message:

'R'

Should be sent as a response to the UART->Cell gateway asserting the wake up pin of the roadrunner board. UART->Cell gateway will then send a received packet from the server as a response to this ready message. 


## Message formats from UART->Cell gateway

### Ready message:

'R'

Sent as a response to the wake pin of the nrf9160 being asserted. 

### Acknowledge/Success:

'A'

Acknowledge that a connection has been successfully established or a message has been successfully sent.

### Not acknowledge/Fail

'N'

Connection was not able to be established or message was not able to be sent. 