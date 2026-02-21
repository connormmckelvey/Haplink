"""
Core Haplink protocol implementation.

This module contains the low-level packet handling, protocol definition,
and core communication logic for the Haplink serial protocol.
"""

import struct
import time
from enum import Enum
from typing import Optional, Dict, Any, Tuple
import serial


class HaplinkError(Exception):
    """Base exception for Haplink errors."""
    pass


class ConnectionError(HaplinkError):
    """Raised when connection to device fails."""
    pass


class ProtocolError(HaplinkError):
    """Raised when protocol violation occurs."""
    pass


class PacketType(Enum):
    """Haplink packet types."""
    PARAM_WRITE = 0xA1
    PARAM_READ = 0xA2
    TELEMETRY = 0xB1
    HEARTBEAT = 0xC1


class DataType(Enum):
    """Supported data types for Haplink communication."""
    UINT8 = (1, 'B', 1)
    INT16 = (2, 'h', 2)
    INT32 = (3, 'i', 4)
    FLOAT = (4, 'f', 4)
    DOUBLE = (5, 'd', 8)

    def __init__(self, code: int, format_char: str, size: int):
        self.code = code
        self.format_char = format_char
        self.size = size

    @staticmethod
    def from_code(code: int) -> 'DataType':
        """Get DataType from numeric code."""
        for dt in DataType:
            if dt.code == code:
                return dt
        raise ValueError(f"Unknown data type code: {code}")


class HaplinkPacket:
    """
    Represents a Haplink protocol packet.

    Structure (13 bytes):
        Byte 0: Header (0xAA)
        Byte 1: Packet Type
        Byte 2: ID
        Byte 3: Data Type
        Bytes 4-11: Data (8 bytes)
        Byte 12: Checksum
    """

    HEADER = 0xAA
    PACKET_SIZE = 13
    DATA_SIZE = 8

    def __init__(
        self,
        packet_type: PacketType,
        packet_id: int,
        data_type: DataType,
        data: bytes = b'\x00' * 8
    ):
        """
        Create a Haplink packet.

        Args:
            packet_type: Type of packet to send
            packet_id: Identifier for parameter or telemetry variable
            data_type: Data type of payload
            data: Payload bytes (must be 8 bytes, padded with zeros)

        Raises:
            ValueError: If data is not 8 bytes
        """
        if len(data) != self.DATA_SIZE:
            raise ValueError(f"Packet data must be exactly {self.DATA_SIZE} bytes")

        self.packet_type = packet_type
        self.packet_id = packet_id
        self.data_type = data_type
        self.data = data
        self.checksum = self._compute_checksum()

    def _compute_checksum(self) -> int:
        """Compute XOR checksum for packet."""
        checksum = 0
        checksum ^= self.packet_type.value
        checksum ^= self.packet_id
        checksum ^= self.data_type.code
        for byte in self.data:
            checksum ^= byte
        return checksum

    def to_bytes(self) -> bytes:
        """Convert packet to bytes for transmission."""
        packet = bytearray()
        packet.append(self.HEADER)
        packet.append(self.packet_type.value)
        packet.append(self.packet_id)
        packet.append(self.data_type.code)
        packet.extend(self.data)
        packet.append(self.checksum)
        return bytes(packet)

    @staticmethod
    def from_bytes(data: bytes) -> 'HaplinkPacket':
        """
        Parse a packet from raw bytes.

        Args:
            data: Exactly 13 bytes of packet data

        Returns:
            Parsed HaplinkPacket

        Raises:
            ProtocolError: If packet is malformed or checksum fails
        """
        if len(data) != HaplinkPacket.PACKET_SIZE:
            raise ProtocolError(f"Invalid packet size: {len(data)}")

        header = data[0]
        if header != HaplinkPacket.HEADER:
            raise ProtocolError(f"Invalid header: 0x{header:02X}")

        packet_type_val = data[1]
        try:
            packet_type = PacketType(packet_type_val)
        except ValueError:
            raise ProtocolError(f"Unknown packet type: 0x{packet_type_val:02X}")

        packet_id = data[2]

        data_type_code = data[3]
        try:
            data_type = DataType.from_code(data_type_code)
        except ValueError:
            raise ProtocolError(f"Unknown data type: {data_type_code}")

        payload = bytes(data[4:12])
        checksum = data[12]

        packet = HaplinkPacket(packet_type, packet_id, data_type, payload)

        if packet.checksum != checksum:
            raise ProtocolError(
                f"Checksum mismatch: computed 0x{packet.checksum:02X}, "
                f"received 0x{checksum:02X}"
            )

        return packet


class SerialPort:
    """
    Manages low-level serial port operations.

    Handles reading/writing complete packets with timeout and error handling.
    """

    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 0.01):
        """
        Initialize serial port (does not open connection).

        Args:
            port: Serial port name (e.g., 'COM5', '/dev/ttyUSB0')
            baudrate: Baud rate for communication
            timeout: Timeout for read operations (seconds)
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None

    def open(self) -> None:
        """
        Open the serial port.

        Raises:
            ConnectionError: If port cannot be opened
        """
        try:
            self.ser = serial.Serial(
                self.port,
                self.baudrate,
                timeout=self.timeout
            )
            # Allow Arduino to reset
            time.sleep(2)
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
        except serial.SerialException as e:
            raise ConnectionError(f"Failed to open {self.port}: {e}")

    def close(self) -> None:
        """Close the serial port."""
        if self.ser and self.ser.is_open:
            self.ser.close()

    def is_open(self) -> bool:
        """Check if port is open."""
        return self.ser is not None and self.ser.is_open

    def write_packet(self, packet: HaplinkPacket) -> None:
        """
        Write a complete packet to the device.

        Args:
            packet: Packet to send

        Raises:
            HaplinkError: If not connected or write fails
        """
        if not self.is_open():
            raise HaplinkError("Serial port not open")

        try:
            self.ser.write(packet.to_bytes())
        except serial.SerialException as e:
            raise HaplinkError(f"Failed to write packet: {e}")

    def read_packet(self) -> Optional[HaplinkPacket]:
        """
        Read a complete packet from the device.

        Blocks until a complete packet is received or timeout occurs.
        Handles partial packets and synchronization.

        Returns:
            Parsed HaplinkPacket, or None if timeout/no data

        Raises:
            ProtocolError: If malformed packet received
        """
        if not self.is_open():
            raise HaplinkError("Serial port not open")

        # Wait for start byte
        while True:
            byte = self.ser.read(1)
            if not byte:
                return None  # Timeout
            if byte[0] == HaplinkPacket.HEADER:
                break

        # Read remaining packet bytes
        remaining = HaplinkPacket.PACKET_SIZE - 1
        packet_data = byte
        while len(packet_data) < HaplinkPacket.PACKET_SIZE:
            chunk = self.ser.read(remaining - len(packet_data) + 1)
            if not chunk:
                return None  # Timeout during packet read
            packet_data += chunk

        # Parse and validate packet
        try:
            return HaplinkPacket.from_bytes(packet_data[:HaplinkPacket.PACKET_SIZE])
        except ProtocolError as e:
            raise e
