"""
High-level Haplink client interface.

Provides a user-friendly API for parameter management and telemetry streaming.
"""

from typing import Optional, Dict, Any, Union
from struct import pack, unpack
import time

from .haplink_core import (
    SerialPort,
    HaplinkPacket,
    HaplinkError,
    ProtocolError,
    PacketType,
    DataType,
)


class ParamBinding:
    """Represents a registered parameter."""

    def __init__(self, param_id: int, name: str, data_type: DataType):
        self.param_id = param_id
        self.name = name
        self.data_type = data_type
        self._value: Any = None

    def __repr__(self) -> str:
        return f"ParamBinding({self.name}:{self.data_type.name})"


class TelemetryBinding:
    """Represents a registered telemetry variable."""

    def __init__(self, tel_id: int, name: str, data_type: DataType):
        self.tel_id = tel_id
        self.name = name
        self.data_type = data_type
        self._value: Any = None
        self._last_update: float = 0.0

    def __repr__(self) -> str:
        return f"TelemetryBinding({self.name}:{self.data_type.name})"


class Haplink:
    """
    High-level client for Haplink protocol communication.

    Manages parameter and telemetry registration, provides clean API for
    reading/writing device state over serial connection.

    Example:
        >>> haplink = Haplink('COM5')
        >>> haplink.connect()
        >>> 
        >>> # Register and control
        >>> haplink.register_param(1, 'speed', DataType.FLOAT)
        >>> haplink.set_param('speed', 0.5)
        >>> 
        >>> # Stream telemetry
        >>> haplink.register_telemetry(1, 'position', DataType.FLOAT)
        >>> haplink.update()
        >>> pos = haplink.get_telemetry('position')
    """

    # Firmware constraints (must match C++ library)
    MAX_PARAMS = 32
    MAX_TELEMETRY = 32

    def __init__(
        self,
        port: str,
        baudrate: int = 115200,
        timeout: float = 0.01,
        connection_timeout: float = 2.0
    ):
        """
        Initialize Haplink client.

        Args:
            port: Serial port (e.g., 'COM5', '/dev/ttyUSB0')
            baudrate: Baud rate (default 115200)
            timeout: Serial read timeout in seconds (default 0.01 for non-blocking)
            connection_timeout: Max time to wait for device response
        """
        self._serial = SerialPort(port, baudrate, timeout)
        self._connection_timeout = connection_timeout

        # Registries
        self._params: Dict[int, ParamBinding] = {}
        self._params_by_name: Dict[str, ParamBinding] = {}
        self._telemetry: Dict[int, TelemetryBinding] = {}
        self._telemetry_by_name: Dict[str, TelemetryBinding] = {}

        # Connection state
        self._connected = False
        self._last_packet_time = 0.0

    def connect(self) -> bool:
        """
        Connect to the device.

        Opens serial port and verifies device is responding by reading
        any available data within the timeout window.

        Returns:
            True if device detected, False if no response within timeout
        """
        try:
            self._serial.open()
        except HaplinkError as e:
            raise ConnectionError(f"Failed to connect: {e}")

        # Try to detect device by reading packets
        start_time = time.time()
        while time.time() - start_time < self._connection_timeout:
            try:
                packet = self._serial.read_packet()
                if packet is not None:
                    self._connected = True
                    self._last_packet_time = time.time()
                    return True
            except ProtocolError:
                continue

        # No response from device
        self._serial.close()
        return False

    def disconnect(self) -> None:
        """Disconnect from the device."""
        self._serial.close()
        self._connected = False

    def is_connected(self) -> bool:
        """Check if connected to device."""
        return self._connected

    def register_param(
        self,
        param_id: int,
        name: str,
        data_type: DataType
    ) -> None:
        """
        Register a parameter that can be written to from host.

        Parameters are variables on the device that can be read or modified
        from the host. Use the same ID as registered on the device.

        Args:
            param_id: Unique parameter ID (0-255, must match device)
            name: Human-readable name for this parameter
            data_type: Data type of the parameter

        Raises:
            ValueError: If parameter ID already registered or invalid
        """
        if param_id in self._params:
            raise ValueError(f"Parameter {param_id} already registered")
        if name in self._params_by_name:
            raise ValueError(f"Parameter name '{name}' already registered")
        if not 0 <= param_id <= 255:
            raise ValueError("Parameter ID must be 0-255")
        if len(self._params) >= self.MAX_PARAMS:
            raise ValueError(f"Maximum {self.MAX_PARAMS} parameters allowed (limit enforced by firmware)")

        binding = ParamBinding(param_id, name, data_type)
        self._params[param_id] = binding
        self._params_by_name[name] = binding

    def register_telemetry(
        self,
        tel_id: int,
        name: str,
        data_type: DataType
    ) -> None:
        """
        Register a telemetry variable to stream from device.

        Telemetry variables are streamed from the device to the host.
        Use the same ID as registered on the device.

        Args:
            tel_id: Unique telemetry ID (0-255, must match device)
            name: Human-readable name for this variable
            data_type: Data type of the telemetry

        Raises:
            ValueError: If telemetry ID already registered or invalid
        """
        if tel_id in self._telemetry:
            raise ValueError(f"Telemetry {tel_id} already registered")
        if name in self._telemetry_by_name:
            raise ValueError(f"Telemetry name '{name}' already registered")
        if not 0 <= tel_id <= 255:
            raise ValueError("Telemetry ID must be 0-255")
        if len(self._telemetry) >= self.MAX_TELEMETRY:
            raise ValueError(f"Maximum {self.MAX_TELEMETRY} telemetry variables allowed (limit enforced by firmware)")

        binding = TelemetryBinding(tel_id, name, data_type)
        self._telemetry[tel_id] = binding
        self._telemetry_by_name[name] = binding

    def set_param(self, param_name: str, value: Union[int, float]) -> None:
        """
        Write a parameter value to the device.

        Args:
            param_name: Name of parameter to write
            value: Value to write

        Raises:
            ValueError: If parameter not registered
            HaplinkError: If not connected or write fails
        """
        if param_name not in self._params_by_name:
            raise ValueError(f"Parameter '{param_name}' not registered")

        if not self._connected:
            raise HaplinkError("Not connected to device")

        param = self._params_by_name[param_name]
        payload = self._encode_value(value, param.data_type)

        packet = HaplinkPacket(
            PacketType.PARAM_WRITE,
            param.param_id,
            param.data_type,
            payload
        )

        self._serial.write_packet(packet)
        
        # Store the value locally so get_param_value() returns what we sent
        param._value = value

    def get_telemetry(self, tel_name: str) -> Any:
        """
        Get the last received telemetry value.

        Returns the most recent value received from the device.
        Returns None if no data has been received yet.

        Args:
            tel_name: Name of telemetry variable

        Returns:
            Last received value, or None if not yet received

        Raises:
            ValueError: If telemetry not registered
        """
        if tel_name not in self._telemetry_by_name:
            raise ValueError(f"Telemetry '{tel_name}' not registered")

        tel = self._telemetry_by_name[tel_name]
        return tel._value

    def update(self, debug: bool = False) -> int:
        """
        Process incoming telemetry packets from device.

        Call this regularly (e.g., in main loop) to receive and buffer
        telemetry data from the device. Reads all available packets.
        
        Args:
            debug: If True, print debug information about packets received
            
        Returns:
            Number of packets successfully processed
        """
        if not self._connected:
            return 0

        # Read all available packets (don't just read one)
        packets_read = 0
        errors = 0
        while packets_read < 100:  # Prevent infinite loop
            try:
                packet = self._serial.read_packet()
            except ProtocolError as e:
                errors += 1
                if debug and errors <= 3:
                    print(f"[DEBUG] ProtocolError: {e}")
                continue  # Skip malformed packets, try next

            if packet is None:
                break  # No more data available

            packets_read += 1
            self._last_packet_time = time.time()

            if debug and packets_read <= 5:
                print(f"[DEBUG] Packet received: type={packet.packet_type.name}, id={packet.packet_id}")

            # Handle telemetry packets
            if packet.packet_type == PacketType.TELEMETRY:
                if packet.packet_id in self._telemetry:
                    tel = self._telemetry[packet.packet_id]
                    value = self._decode_value(packet.data, tel.data_type)
                    
                    # Debug: Show what we're decoding
                    if debug and packets_read <= 5:
                        hex_str = ' '.join([f'{b:02X}' for b in packet.data[:8]])
                        print(f"[DEBUG] ID {packet.packet_id}: hex={hex_str}, decoded={value}")
                    
                    tel._value = value
                    tel._last_update = time.time()
                elif debug:
                    print(f"[DEBUG] Unknown telemetry ID: {packet.packet_id}")
        
        if debug and packets_read > 0:
            print(f"[DEBUG] update() processed {packets_read} packets, {errors} errors")
        
        return packets_read

    def get_telemetry_all(self) -> Dict[str, Any]:
        """
        Get all registered telemetry values.

        Returns:
            Dictionary mapping telemetry names to last received values
        """
        return {name: tel._value for name, tel in self._telemetry_by_name.items()}

    def get_param_value(self, param_name: str) -> Any:
        """
        Get the last written parameter value (cached locally).

        This returns the value we sent to the device, not a value read from it.

        Args:
            param_name: Name of parameter

        Returns:
            Last written value

        Raises:
            ValueError: If parameter not registered
        """
        if param_name not in self._params_by_name:
            raise ValueError(f"Parameter '{param_name}' not registered")

        return self._params_by_name[param_name]._value

    def list_params(self) -> Dict[str, Dict[str, Any]]:
        """
        List all registered parameters.

        Returns:
            Dictionary mapping parameter names to their properties
        """
        result = {}
        for name, param in self._params_by_name.items():
            result[name] = {
                'id': param.param_id,
                'type': param.data_type.name,
                'value': param._value
            }
        return result

    def list_telemetry(self) -> Dict[str, Dict[str, Any]]:
        """
        List all registered telemetry variables.

        Returns:
            Dictionary mapping names to their properties and last values
        """
        result = {}
        for name, tel in self._telemetry_by_name.items():
            result[name] = {
                'id': tel.tel_id,
                'type': tel.data_type.name,
                'value': tel._value,
                'last_update': tel._last_update
            }
        return result

    @staticmethod
    def _encode_value(value: Union[int, float], data_type: DataType) -> bytes:
        """Encode a Python value to bytes according to data type."""
        if data_type == DataType.UINT8:
            encoded = pack('B', int(value))
        elif data_type == DataType.INT16:
            encoded = pack('h', int(value))
        elif data_type == DataType.INT32:
            encoded = pack('i', int(value))
        elif data_type == DataType.FLOAT:
            encoded = pack('f', float(value))
        elif data_type == DataType.DOUBLE:
            encoded = pack('d', float(value))
        else:
            raise ValueError(f"Unknown data type: {data_type}")

        # Pad to 8 bytes
        return encoded + b'\x00' * (8 - len(encoded))

    @staticmethod
    def _decode_value(data: bytes, data_type: DataType) -> Union[int, float]:
        """Decode bytes to a Python value according to data type."""
        if data_type == DataType.UINT8:
            return unpack('B', data[:1])[0]
        elif data_type == DataType.INT16:
            return unpack('h', data[:2])[0]
        elif data_type == DataType.INT32:
            return unpack('i', data[:4])[0]
        elif data_type == DataType.FLOAT:
            return unpack('f', data[:4])[0]
        elif data_type == DataType.DOUBLE:
            return unpack('d', data[:8])[0]
        else:
            raise ValueError(f"Unknown data type: {data_type}")
