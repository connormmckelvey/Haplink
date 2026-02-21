# Haplink

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

**Haplink** is a lightweight, high-performance communication library for haptic robotic devices. It provides a robust bidirectional serial protocol for real-time parameter control and telemetry streaming between embedded devices (Arduino/microcontrollers) and host computers (Python).

---

## Features

### Core Capabilities
- **Bidirectional Communication**: Send parameters to devices and receive telemetry data
- **Type-Safe Protocol**: Support for UINT8, INT16, INT32, FLOAT, and DOUBLE data types
- **Real-Time Performance**: Optimized for low-latency control loops in haptic applications
- **Error Detection**: XOR checksum validation for reliable data transmission
- **Simple API**: Clean, intuitive interfaces for both firmware and host software

### Firmware (C++ for Arduino)
- Zero-copy packet parsing
- Interrupt-safe design
- Registry-based variable binding (up to 32 parameters + 32 telemetry variables)
- Minimal memory footprint
- **[Full Firmware Documentation](firmware/README.md)**

### Python Client
- Object-oriented API with type hints
- Automatic packet synchronization
- Connection management with timeout detection
- Human-readable variable naming
- **[Full Python Documentation](python/README.md)**

---

## Installation

### Python Client

**Install directly from GitHub**:
```bash
# Latest version
pip install git+https://github.com/ConnorMcKelvey/Haplink.git#subdirectory=python

# Or clone and install
git clone https://github.com/ConnorMcKelvey/Haplink.git
cd Haplink/python
pip install .
```

**Requirements**: Python 3.8+ and `pyserial>=3.5`

**[→ Detailed Python installation guide](python/README.md)**

### Firmware Library (Arduino)
**Install if using Platform.io**:
```ini
#inside your platformio.ini
lib_deps =
    https://github.com/ConnorMcKelvey/Haplink.git
```
**Install from GitHub**:
```bash
# Clone the repository
git clone https://github.com/ConnorMcKelvey/Haplink.git

# Copy to Arduino libraries
# Windows:
cp -r Haplink/firmware/src ~/Documents/Arduino/libraries/Haplink
# macOS/Linux:
cp -r Haplink/firmware/src ~/Arduino/libraries/Haplink
```

Then restart Arduino IDE and use: `#include <haplink.h>`

**[→ Detailed firmware installation guide](firmware/README.md)**

---

## Quick Start

### Firmware Side (Arduino)

```cpp
#include <haplink.h>

Haplink haplink;

// Variables to expose
float targetPosition = 0.0;
float currentPosition = 0.0;
float currentVelocity = 0.0;

void setup() {
    Serial.begin(115200);
    
    // Initialize Haplink with Serial port
    haplink.begin(Serial);
    
    // Register parameter (writable from host)
    haplink.registerParam(1, &targetPosition, HL_FLOAT);
    
    // Register telemetry (readable by host)
    haplink.registerTelemetry(1, &currentPosition, HL_FLOAT);
    haplink.registerTelemetry(2, &currentVelocity, HL_FLOAT);
}

void loop() {
    // Process incoming commands
    haplink.update();
    
    // Your control logic here
    currentPosition += currentVelocity * 0.01;
    currentVelocity = (targetPosition - currentPosition) * 0.5;
    
    // Send telemetry data (optional: automatic streaming coming soon)
    haplink.sendTelemetry(1); // Send position
    haplink.sendTelemetry(2); // Send velocity
    
    delay(10); // 100 Hz loop
}
```

### Python Side (Host)

```python
from haplink import Haplink, DataType
import time

# Connect to device
haplink = Haplink('COM5', baudrate=115200)  # Use '/dev/ttyUSB0' on Linux
haplink.connect()

# Register variables (IDs must match Arduino sketch)
haplink.register_param(1, 'target_position', DataType.FLOAT)
haplink.register_telemetry(1, 'current_position', DataType.FLOAT)
haplink.register_telemetry(2, 'current_velocity', DataType.FLOAT)

# Control loop
for i in range(100):
    # Receive telemetry from device
    haplink.update()
    
    # Read telemetry values
    position = haplink.get_telemetry('current_position')
    velocity = haplink.get_telemetry('current_velocity')
    
    # Send new target position
    target = 0.5 * (1 + i / 100.0)
    haplink.set_param('target_position', target)
    
    print(f"Target: {target:.3f} | Position: {position} | Velocity: {velocity}")
    time.sleep(0.01)

# Cleanup
haplink.disconnect()
```

---

## Documentation

### Complete API References

- **[Firmware API Documentation](firmware/README.md)** - Complete C++/Arduino API reference with examples
- **[Python API Documentation](python/README.md)** - Complete Python client API reference

### Quick API Overview

#### Python
```python
# Connection
haplink = Haplink('COM5', baudrate=115200)
haplink.connect()

# Registration
haplink.register_param(id, 'name', DataType.FLOAT)
haplink.register_telemetry(id, 'name', DataType.FLOAT)

# Usage
haplink.set_param('name', value)
value = haplink.get_telemetry('name')
haplink.update()  # Call regularly
```

#### Arduino
```cpp
// Initialization
haplink.begin(Serial);

// Registration
haplink.registerParam(id, &variable, HL_FLOAT);
haplink.registerTelemetry(id, &variable, HL_FLOAT);

// Usage
haplink.update();  // Call in loop()
haplink.sendTelemetry(id);
haplink.sendAllTelemetry();
```

---

## Protocol Specification

Haplink uses a simple, robust 13-byte packet protocol optimized for real-time communication.

### Packet Structure (13 bytes)

| Byte | Field       | Description                           |
|------|-------------|---------------------------------------|
| 0    | Header      | Start byte (0xAA)                     |
| 1    | Packet Type | Command type                          |
| 2    | ID          | Parameter or telemetry identifier     |
| 3    | Data Type   | Type code (1-5)                       |
| 4-11 | Data        | Payload (8 bytes, little-endian)      |
| 12   | Checksum    | XOR of bytes 1-11                     |

### Packet Types

| Type          | Code | Direction     | Description             |
|---------------|------|---------------|-------------------------|
| PARAM_WRITE   | 0xA1 | Host → Device | Write parameter value   |
| PARAM_READ    | 0xA2 | Host → Device | Request parameter value |
| TELEMETRY     | 0xB1 | Device → Host | Stream telemetry data   |
| HEARTBEAT     | 0xC1 | Bidirectional | Keep-alive signal       |

### Supported Data Types

- **UINT8** (1 byte): Unsigned 8-bit integer
- **INT16** (2 bytes): Signed 16-bit integer
- **INT32** (4 bytes): Signed 32-bit integer
- **FLOAT** (4 bytes): IEEE 754 single-precision
- **DOUBLE** (8 bytes): IEEE 754 double-precision

All data is little-endian and padded to 8 bytes. Packets use XOR checksum for error detection.

---

## Examples

### Complete Position Control System

**Arduino** ([more examples →](firmware/README.md#-usage-examples)):
```cpp
#include <haplink.h>

Haplink haplink;
float targetPos = 0.0;
float currentPos = 0.0;

void setup() {
    Serial.begin(115200);
    haplink.begin(Serial);
    haplink.registerParam(1, &targetPos, HL_FLOAT);
    haplink.registerTelemetry(1, &currentPos, HL_FLOAT);
}

void loop() {
    haplink.update();
    currentPos += (targetPos - currentPos) * 0.1;  // Simple controller
    haplink.sendTelemetry(1);
    delay(10);
}
```

**Python** ([more examples →](python/examples/)):
```python
from haplink import Haplink, DataType
import time

haplink = Haplink('COM5')
haplink.connect()
haplink.register_param(1, 'target', DataType.FLOAT)
haplink.register_telemetry(1, 'position', DataType.FLOAT)

for angle in range(0, 360, 5):
    target = angle / 360.0
    haplink.set_param('target', target)
    haplink.update()
    print(f"Pos: {haplink.get_telemetry('position'):.2f}")
    time.sleep(0.05)

haplink.disconnect()
```

**See also**:
- [Firmware Examples](firmware/README.md#-usage-examples) - Multi-sensor streaming, safety features, multiple serial ports
- [Python Examples](python/examples/) - Complete working examples

---

## Troubleshooting

### Common Issues

| Issue | Quick Fix |
|-------|-----------|
| `connect()` returns False | Verify port name, check baud rate matches (115200), ensure Arduino is powered |
| Telemetry stays `None` | Call `haplink.update()` in Python loop, call `sendTelemetry()` in Arduino |
| Variables not updating | Ensure IDs match on both sides, check data types match |
| Checksum errors | Try lower baud rate, check USB cable quality |

**For detailed troubleshooting guides**:
- [Python Troubleshooting](python/README.md#troubleshooting) 
- [Firmware Troubleshooting](firmware/README.md#-troubleshooting)

---

## Development

### Building from Source

```bash
git clone https://github.com/ConnorMcKelvey/Haplink.git
cd Haplink

# Python development
cd python
pip install -e .[dev]  # Installs with pytest, black, ruff, mypy
```

### Testing

```bash
cd python
pytest                    # Run tests
pytest --cov=haplink     # With coverage
```

---

## Project Roadmap

- [ ] Automatic telemetry streaming (push from firmware)
- [ ] Parameter read requests (query device state)
- [ ] Heartbeat/keepalive mechanism
- [ ] CRC-16 checksum option
- [ ] PlatformIO library support
- [ ] PyPI package publication
- [ ] More examples and tutorials

---

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Author

**Connor McKelvey**
- Email: ConnorMcKelvey@utexas.edu
- GitHub: [@ConnorMcKelvey](https://github.com/ConnormMcKelvey)

---

## Acknowledgments

Built for the haptic robotics research community. Special thanks to all contributors and the University of Texas Haptics research group.

---

## Support & Resources

- **[Issues](https://github.com/ConnorMcKelvey/Haplink/issues)** - Bug reports and feature requests
- **[Firmware Documentation](firmware/README.md)** - Complete Arduino/C++ guide
- **[Python Documentation](python/README.md)** - Complete Python client guide
- **[Examples](python/examples/)** - Working code examples

---
