# Haplink Python Client

Python client library for communicating with haptic robotic devices over serial connections.

---

## Installation

### From Source

```bash
git clone https://github.com/ConnorMcKelvey/Haplink.git
cd Haplink/python
pip install -e .
```

**Option 3: Editable/development install**
```bash
git clone https://github.com/ConnorMcKelvey/Haplink.git
cd Haplink/python
pip install -e .              # Basic install
pip install -e .[dev]         # With dev tools (pytest, black, ruff, mypy)
```

**Requirements**: Python 3.8+ and `pyserial>=3.5`

---

## Quick Start

```python
from haplink import Haplink, DataType
import time

# Connect to device
haplink = Haplink('COM5', baudrate=115200)  # Use '/dev/ttyUSB0' on Linux
haplink.connect()

# Register variables (IDs must match firmware)
haplink.register_param(1, 'target_position', DataType.FLOAT)
haplink.register_telemetry(1, 'current_position', DataType.FLOAT)

# Control loop
for i in range(100):
    haplink.update()  # Receive telemetry from device
    position = haplink.get_telemetry('current_position')
    haplink.set_param('target_position', i / 100.0)
    print(f"Position: {position}")
    time.sleep(0.01)

haplink.disconnect()
```

---

## API Reference

### Haplink Class

#### Constructor

```python
haplink = Haplink(port: str, baudrate: int = 115200, timeout: float = 0.01, 
                  connection_timeout: float = 2.0)
```

**Parameters**:
- `port`: Serial port name (e.g., `'COM5'`, `'/dev/ttyUSB0'`, `'/dev/ttyACM0'`)
- `baudrate`: Communication speed (default: 115200)
- `timeout`: Serial read timeout in seconds (default: 0.01 for non-blocking)
- `connection_timeout`: Time to wait for device response during connection (default: 2.0)

#### Connection Management

##### `connect()`
```python
haplink.connect() -> bool
```
Open serial connection and verify device is responding.

**Returns**: `True` if successful, `False` if device not detected

**Example**:
```python
if haplink.connect():
    print("Connected!")
else:
    print("Connection failed")
```

##### `disconnect()`
```python
haplink.disconnect()
```
Close the serial connection.

##### `is_connected()`
```python
haplink.is_connected() -> bool
```
Check if currently connected to device.

#### Variable Registration

##### `register_param()`
```python
haplink.register_param(param_id: int, name: str, data_type: DataType)
```

Register a parameter that can be **written to the device**.

**Parameters**:
- `param_id`: Unique ID (0-255) - **must match firmware**
- `name`: Human-readable name for this parameter
- `data_type`: One of `DataType.UINT8`, `INT16`, `INT32`, `FLOAT`, `DOUBLE`

**Raises**: `ValueError` if ID or name already registered, or registry full (max 32)

**Example**:
```python
haplink.register_param(1, 'motor_speed', DataType.FLOAT)
haplink.register_param(2, 'enable', DataType.UINT8)
```

##### `register_telemetry()`
```python
haplink.register_telemetry(tel_id: int, name: str, data_type: DataType)
```

Register a telemetry variable to **receive from the device**.

**Parameters**:
- `tel_id`: Unique ID (0-255) - **must match firmware**
- `name`: Human-readable name
- `data_type`: Data type

**Raises**: `ValueError` if ID or name already registered, or registry full (max 32)

**Example**:
```python
haplink.register_telemetry(1, 'position', DataType.FLOAT)
haplink.register_telemetry(2, 'velocity', DataType.FLOAT)
```

#### Data Transfer

##### `set_param()`
```python
haplink.set_param(param_name: str, value: Union[int, float])
```

Write a parameter value to the device.

**Parameters**:
- `param_name`: Name of registered parameter
- `value`: Value to write

**Example**:
```python
haplink.set_param('motor_speed', 0.75)
haplink.set_param('enable', 1)
```

##### `get_telemetry()`
```python
haplink.get_telemetry(tel_name: str) -> Union[int, float, None]
```

Get the most recently received telemetry value.

**Returns**: Last received value, or `None` if no data received yet

**Example**:
```python
position = haplink.get_telemetry('position')
if position is not None:
    print(f"Position: {position}")
```

##### `update()`
```python
haplink.update(debug: bool = False) -> int
```

Process incoming telemetry packets. **Call this regularly** in your control loop.

**Parameters**:
- `debug`: If `True`, print debug information about received packets

**Returns**: Number of packets successfully processed

**Example**:
```python
while True:
    num_packets = haplink.update()
    # Your control code
    time.sleep(0.01)
```

#### Utility Methods

##### `get_telemetry_all()`
```python
haplink.get_telemetry_all() -> Dict[str, Any]
```

Get all registered telemetry values as a dictionary.

**Example**:
```python
all_data = haplink.get_telemetry_all()
print(all_data)  # {'position': 0.5, 'velocity': 0.1}
```

##### `list_params()`
```python
haplink.list_params() -> Dict[str, Dict[str, Any]]
```

List all registered parameters with their properties.

**Returns**: Dictionary with parameter info (id, type, last value)

##### `list_telemetry()`
```python
haplink.list_telemetry() -> Dict[str, Dict[str, Any]]
```

List all registered telemetry variables with their properties.

**Returns**: Dictionary with telemetry info (id, type, last value, last update time)

### Data Types

```python
from haplink import DataType

DataType.UINT8   # Unsigned 8-bit: 0 to 255
DataType.INT16   # Signed 16-bit: -32768 to 32767
DataType.INT32   # Signed 32-bit: -2147483648 to 2147483647
DataType.FLOAT   # 32-bit float: ±3.4e38 (7 digits precision)
DataType.DOUBLE  # 64-bit float: ±1.7e308 (15 digits precision)
```

### Exception Classes

```python
from haplink import HaplinkError, ProtocolError, HaplinkConnectionError

HaplinkError           # Base exception for all Haplink errors
ProtocolError          # Raised on protocol violations (checksum, format)
HaplinkConnectionError # Raised on connection failures
```

---

## Usage Examples

### Example 1: Motor Control with Feedback

```python
from haplink import Haplink, DataType
import time

haplink = Haplink('COM5')
haplink.connect()

# Setup
haplink.register_param(1, 'target_speed', DataType.FLOAT)
haplink.register_telemetry(1, 'actual_speed', DataType.FLOAT)
haplink.register_telemetry(2, 'motor_current', DataType.FLOAT)

# Control loop
for speed in [0.2, 0.5, 0.8, 0.5, 0.0]:
    haplink.set_param('target_speed', speed)
    
    for _ in range(50):  # Run for 0.5 seconds
        haplink.update()
        actual = haplink.get_telemetry('actual_speed')
        current = haplink.get_telemetry('motor_current')
        print(f"Target: {speed:.1f} | Actual: {actual} | Current: {current}A")
        time.sleep(0.01)

haplink.disconnect()
```

### Example 2: Multi-Sensor Data Logging

```python
from haplink import Haplink, DataType
import time
import csv

haplink = Haplink('/dev/ttyUSB0')  # Linux
haplink.connect()

# Register multiple sensors
haplink.register_telemetry(1, 'temperature', DataType.FLOAT)
haplink.register_telemetry(2, 'pressure', DataType.FLOAT)
haplink.register_telemetry(3, 'humidity', DataType.FLOAT)

# Log data to CSV
with open('sensor_log.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['Time', 'Temperature', 'Pressure', 'Humidity'])
    
    start_time = time.time()
    for _ in range(1000):  # 10 seconds at 100 Hz
        haplink.update()
        
        data = haplink.get_telemetry_all()
        elapsed = time.time() - start_time
        writer.writerow([elapsed, data['temperature'], 
                        data['pressure'], data['humidity']])
        
        time.sleep(0.01)

haplink.disconnect()
```

### Example 3: Real-Time Plotting

```python
from haplink import Haplink, DataType
import matplotlib.pyplot as plt
import matplotlib.animation as animation

haplink = Haplink('COM5')
haplink.connect()
haplink.register_telemetry(1, 'signal', DataType.FLOAT)

# Setup plot
fig, ax = plt.subplots()
x_data, y_data = [], []
line, = ax.plot([], [])
ax.set_ylim(-1, 1)

def update_plot(frame):
    haplink.update()
    value = haplink.get_telemetry('signal')
    if value is not None:
        x_data.append(frame)
        y_data.append(value)
        if len(x_data) > 100:
            x_data.pop(0)
            y_data.pop(0)
        line.set_data(x_data, y_data)
        ax.set_xlim(max(0, frame-100), frame)
    return line,

ani = animation.FuncAnimation(fig, update_plot, interval=10)
plt.show()
haplink.disconnect()
```

---

## Troubleshooting

### Connection Issues

**Problem**: `connect()` returns `False`

**Solutions**:
1. **Verify port name**:
   - Windows: Check Device Manager → Ports (COM & LPT) → `COM5`
   - Linux: `ls /dev/ttyUSB*` or `ls /dev/ttyACM*`
   - macOS: `ls /dev/tty.*`
2. **Check baud rate** matches firmware (default: 115200)
3. **Verify Arduino is powered** and USB cable is connected
4. **Wait for Arduino reset** (takes ~2 seconds after connection)

### Data Not Updating

**Problem**: `get_telemetry()` always returns `None`

**Solutions**:
1. **Call `update()` regularly** - this is what receives data!
2. **Verify IDs match** between Python and firmware
3. **Check Arduino code** is calling `sendTelemetry()` or `sendAllTelemetry()`
4. **Use debug mode**: `haplink.update(debug=True)` to see packet info

### Serial Port Permission (Linux)

**Problem**: `PermissionError: [Errno 13] Permission denied: '/dev/ttyUSB0'`

**Solution**:
```bash
sudo usermod -a -G dialout $USER
# Log out and back in for changes to take effect
```

Or temporarily:
```bash
sudo chmod 666 /dev/ttyUSB0
```

### Mixed-up Data

**Problem**: Telemetry values seem wrong or swapped

**Solutions**:
1. **Verify data types match** on both sides (e.g., both use `FLOAT`)
2. **Check ID numbers** - they must be identical on firmware and Python
3. **Restart both** Arduino and Python script to clear any state

### Performance Issues

**Problem**: Control loop is slow or laggy

**Solutions**:
1. **Reduce telemetry rate** on Arduino side
2. **Batch telemetry** using `sendAllTelemetry()` instead of individual calls
3. **Check timeout value** - lower timeout = faster response: `Haplink(port, timeout=0.001)`
4. **Increase baud rate** to 230400 or higher (must match on both sides)

---

## See Also

- **[Main Project README](../README.md)** - Overview and protocol details
- **[Firmware Documentation](../firmware/README.md)** - Arduino/C++ API reference
- **[Complete Examples](examples/)** - Working code examples

---

## License

MIT License - see [LICENSE](https://github.com/ConnorMcKelvey/Haplink/blob/main/LICENSE) for details.

---

## Support

- **Issues**: [GitHub Issues](https://github.com/ConnorMcKelvey/Haplink/issues)
- **Email**: ConnorMcKelvey@utexas.edu
