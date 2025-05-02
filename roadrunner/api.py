from __future__ import annotations
import os
import sys
import struct
from dataclasses import dataclass, field
from typing import Union

from mpio import GPIO, DevMem
from serial import Serial


if sys.version_info >= (3, 11):
    from enum import StrEnum
else:
    from backports.strenum import StrEnum


class Protocol(StrEnum):
    """Defines the protocol to use."""

    IPV4 = "4"
    IPV6 = "6"


@dataclass
class Config:
    """Configuration of the communication channel"""

    protocol: Protocol
    ip: list[int]
    control: int
    stream: int

    pack_format: str = field(default="!1c4B2H", init=False)

    def serialize(self) -> bytes:
        return struct.pack(
            self.pack_format,
            self.protocol.encode("ascii"),
            *self.ip,
            self.stream,
            self.control,
        )

    @classmethod
    def unpack_and_init(cls, ser: Serial):
        ipstr: str
        prot, ipstr, stream, control = struct.unpack(cls.pack_format, ser.read(28))

        ip = list(map(int, ipstr.split(".")))
        return cls(Protocol(prot), ip, int(control), int(stream))


@dataclass
class Payload:
    """Payload for a message"""

    length: int
    data: bytes

    pack_format: str = field(default="!H", init=False)

    def serialize(self) -> bytes:
        return struct.pack(Payload.pack_format, self.length) + self.data

    @classmethod
    def unpack_and_init(cls, ser: Serial) -> Union[Payload, None]:
        length = struct.unpack(cls.pack_format, ser.read(1))
        if not isinstance(length, int):
            return None

        return cls(length, ser.read(length))


class MessageType(StrEnum):
    """The type of mesage"""

    CONTROL = "C"
    STREAM = "S"
    ESTABLISH = "E"
    READY = "R"
    STATUS = "?"
    ACK = "A"
    NACK = "N"


@dataclass
class Message:
    id: MessageType = field(init=False)

    pack_format: str = field(default="!c", init=False)

    def serialize(self) -> bytes:
        """Serializes the message

        Returns:
            bytes: Bytes ready to send on a serial line.
        """
        return struct.pack(self.pack_format, self.id.encode("ascii"))

    @classmethod
    def deserialize(cls, serial: Serial) -> Union[Message, None]:
        """Deserialize incoming message.

        This function reads the incoming bytes on the serial line and
        automatically deserializes and creates the appropriate message object.

        Args:
            ser (Serial): The serial connection to read from

        Returns:
            None: The incoming id has not been recognized.
            Message: The deserialized message.
        """
        id = struct.unpack(cls.pack_format, serial.read(1))

        if id == MessageType.CONTROL:
            return ControlMessage.unpack_and_init(serial)
        elif id == MessageType.STREAM:
            return StreamMessage.unpack_and_init(serial)
        elif id == MessageType.ESTABLISH:
            return EstablishMessage.unpack_and_init(serial)
        elif id == MessageType.READY:
            return ReadyMessage.unpack_and_init(serial)
        elif id == MessageType.STATUS:
            return StatusMessage.unpack_and_init(serial)
        elif id == MessageType.ACK:
            return AckMessage.unpack_and_init(serial)
        elif id == MessageType.NACK:
            return NackMessage.unpack_and_init(serial)
        else:
            return None

    @classmethod
    def unpack_and_init(cls, _ser: Serial):
        """Internal function, do not use!"""
        return cls()


@dataclass
class StatusMessage(Message):
    """A message to query the connection status"""

    id: MessageType = field(default=MessageType.STATUS, init=False)


@dataclass
class AckMessage(Message):
    """A message to acknowledge an action"""

    id: MessageType = field(default=MessageType.ACK, init=False)


@dataclass
class NackMessage(Message):
    """A message to an action that failed"""

    id: MessageType = field(default=MessageType.NACK, init=False)


@dataclass
class ReadyMessage(Message):
    """A message to acknowledge a signal"""

    id: MessageType = field(default=MessageType.READY, init=False)


@dataclass
class EstablishMessage(Message):
    """A message for establishing a connection"""

    id: MessageType = field(default=MessageType.ESTABLISH, init=False)
    config: Config

    def serialize(self) -> bytes:
        return super().serialize() + self.config.serialize()

    @classmethod
    def unpack_and_init(cls, ser: Serial):
        return cls(Config.unpack_and_init(ser))


@dataclass
class ControlMessage(Message):
    """A message for configuring the communication channel"""

    id: MessageType = field(default=MessageType.CONTROL, init=False)
    payload: Payload

    def serialize(self) -> bytes:
        return super().serialize() + self.payload.serialize()

    @classmethod
    def unpack_and_init(cls, ser: Serial):
        payload = Payload.unpack_and_init(ser)
        if payload is None:
            return None
        return cls(payload)


@dataclass
class StreamMessage(Message):
    """A message for sending stream data"""

    id: MessageType = field(default=MessageType.STREAM, init=False)
    payload: Payload

    def serialize(self) -> bytes:
        return super().serialize() + self.payload.serialize()

    @classmethod
    def unpack_and_init(cls, ser: Serial):
        payload = Payload.unpack_and_init(ser)
        if payload is None:
            return None
        return cls(payload)


@dataclass
class Connection:
    """Connection context"""

    ser: Serial
    out_line: GPIO
    in_line: GPIO


def connect(device: str, timeout: int) -> Connection:
    """Open a connection to the nrf.

    Args:
        device (str): The serial port on which the nrf is connected.
        timeout (int): The timeout to set on the serial connection to the nrf.

    Returns:
        Connection: The connection context which you should pass to all other
        functions that interact with the nrf.
    """
    ser = Serial(device, 115200, timeout=timeout)

    out_line = GPIO(1, GPIO.OUT, initial=GPIO.LOW)
    in_line = GPIO(2, GPIO.IN)

    return Connection(ser, out_line, in_line)


def send(connection: Connection, message: Message) -> Message:
    """Send a message.

    Args:
        connection: The connection to the nrf.
        message: The message to send.

    Raises:
        TimeoutError: The serial connection has timed out.

    Returns:
        None: The given message has an unknown type.
        Message: The received message, this may be ack or nack or ...
    """
    connection.out_line.set(GPIO.HIGH)

    ready = Message.deserialize(connection.ser)
    if ready is None:
        raise TimeoutError("The nrf did not react to our wakeup signal!")
    elif not isinstance(ready, ReadyMessage):
        return ready

    connection.out_line.set(GPIO.LOW)

    written = connection.ser.write(message.serialize())
    if written is None:
        raise TimeoutError("Could not write to serial!")

    ack = Message.deserialize(connection.ser)
    if ack is None:
        raise TimeoutError("Did not get an ack for our message!")

    return ack


def recv(connection: Connection) -> Union[None, Message]:
    """Receive a message.

    This function is blocking on the wakeup signal from the nrf.

    Args:
        connection: The connection to the nrf.

    Raises:
        TimeoutError: The serial connection has timed out.

    Returns:
        None: No message was received in the timeout.
        Message: The received message.
    """
    while connection.in_line.get() == GPIO.LOW:
        pass
    written = connection.ser.write(ReadyMessage().serialize())
    if written is None:
        raise TimeoutError("Could not write to serial!")

    return Message.deserialize(connection.ser)


def standby(seconds: int):
    """Go into active standby and wake up after a set time"""

    os.system(f"rtcwake -m standby -s {seconds}")


def suspend_to_ram(seconds: int):
    """Suspend to RAM and wake up after a set time"""

    DevMem.write_reg(0xFC040018, 0x300)
    os.system(f"rtcwake -m mem -s {seconds}")


def shutdown(seconds: int):
    """Shutdown the device and wake up after a set time"""

    os.system(f"sh -c \"echo '+{seconds}' > /sys/class/rtc/rtc0/wakealarm\"")
    os.system("poweroff")


def _woke_up_from_nrf() -> bool:
    address = 0xF8048010
    offset = 0x08
    shdwc_sr = DevMem.read_reg(address + offset)
    if shdwc_sr is None or shdwc_sr & 0x1 == 0:
        return False
    else:
        # WKUP Pin was triggered since last call of this function
        return True
