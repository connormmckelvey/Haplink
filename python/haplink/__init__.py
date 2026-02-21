"""
Haplink - Python Host Communication Module

A professional Python library for communicating with Arduino devices running
the Haplink firmware. Provides high-level abstractions for parameter control
and telemetry streaming over serial connections.

Basic Usage:
    >>> from haplink import Haplink, DataType
    >>> 
    >>> haplink = Haplink('COM5', baudrate=115200)
    >>> haplink.connect()
    >>> 
    >>> # Register variables with IDs
    >>> haplink.register_param(1, 'motor_speed', DataType.FLOAT)
    >>> haplink.register_telemetry(1, 'sensor_reading', DataType.FLOAT)
    >>> 
    >>> # Write parameter
    >>> haplink.set_param('motor_speed', 0.75)
    >>> 
    >>> # Read telemetry
    >>> reading = haplink.get_telemetry('sensor_reading')
    >>> print(f"Sensor: {reading}")
"""

from .haplink_core import (
    DataType,
    PacketType,
    HaplinkError,
    ProtocolError,
    ConnectionError as HaplinkConnectionError,
)
from .haplink_client import Haplink

__version__ = "0.1.0"
__author__ = "Hapkit Team"

__all__ = [
    'Haplink',
    'DataType',
    'PacketType',
    'HaplinkError',
    'ProtocolError',
    'HaplinkConnectionError',
]
