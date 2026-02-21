# Haplink Firmware Library (Arduino/C++)

C++ library for Arduino and embedded systems to enable serial communication with host computers using the Haplink protocol.

---

## Installation

### Method 1: From GitHub (Recommended)

**Step 1: Clone the repository**
```bash
git clone https://github.com/ConnorMcKelvey/Haplink.git
```

**Step 2: Copy to Arduino libraries folder**

**Windows (PowerShell)**:
```powershell
cp -r Haplink/firmware/src ~/Documents/Arduino/libraries/Haplink
```

**macOS/Linux**:
```bash
cp -r Haplink/firmware/src ~/Arduino/libraries/Haplink
```

**Manual copy**: Copy the `firmware/src/` folder to:
- **Windows**: `Documents/Arduino/libraries/Haplink/`
- **macOS**: `~/Documents/Arduino/libraries/Haplink/`
- **Linux**: `~/Arduino/libraries/Haplink/`

The final structure should be:
```
Arduino/libraries/Haplink/
├── haplink.h
├── haplink.cpp
├── haplink_types.h
└── library.properties
```

**Step 3: Restart Arduino IDE**

**Step 4: Verify installation**
```cpp
#include <haplink.h>  // If this compiles, you're good!
```

### Method 2: PlatformIO

Add to your `platformio.ini`:
```ini
lib_deps =
    https://github.com/ConnorMcKelvey/Haplink.git
```

### Method 3: Download ZIP

1. Download from [GitHub releases](https://github.com/ConnorMcKelvey/Haplink/releases) or click "Code" → "Download ZIP"
2. Extract the ZIP file
3. Copy `Haplink-main/firmware/src/` to your Arduino libraries folder as shown above
4. Restart Arduino IDE

---

## Quick Start

### Basic Example

```cpp
#include <haplink.h>

Haplink haplink;

// Variables to control/monitor
float motorSpeed = 0.0;
float sensorValue = 0.0;

void setup() {
    Serial.begin(115200);
    
    // Initialize Haplink
    haplink.begin(Serial);
    
    // Register a parameter (can be written from host)
    haplink.registerParam(1, &motorSpeed, HL_FLOAT);
    
    // Register telemetry (sent to host)
    haplink.registerTelemetry(1, &sensorValue, HL_FLOAT);
}

void loop() {
    // Process incoming commands
    haplink.update();
    
    // Your application logic
    sensorValue = analogRead(A0) / 1023.0;
    
    // Send telemetry to host
    haplink.sendTelemetry(1);
    
    delay(10);  // 100 Hz update rate
}
```

---

## API Reference

### Haplink Class

#### Initialization

##### `begin()`
```cpp
void begin(Stream &serialPort, uint32_t connectionTimeoutMs = 1000)
```

Initialize the Haplink library with a serial port.

**Parameters**:
- `serialPort`: Reference to a Stream object (e.g., `Serial`, `Serial1`, `Serial2`)
- `connectionTimeoutMs`: Time in milliseconds before considering connection dead (default: 1000)

**Example**:
```cpp
Serial.begin(115200);
haplink.begin(Serial);  // Use hardware serial
// or
Serial1.begin(115200);
haplink.begin(Serial1, 2000);  // Use Serial1 with 2-second timeout
```

---

#### Variable Registration

##### `registerParam()`
```cpp
bool registerParam(uint8_t id, void* address, HL_DataType type)
```

Register a variable as a parameter that can be **written from the host**.

**Parameters**:
- `id`: Unique identifier (0-255) - must match Python side
- `address`: Pointer to the variable (`&myVariable`)
- `type`: Data type (see [Data Types](#data-types))

**Returns**: 
- `true` if successful
- `false` if registry is full (max 32 parameters)

**Example**:
```cpp
float targetPosition = 0.0;
int motorEnable = 0;
uint8_t ledBrightness = 0;

haplink.registerParam(1, &targetPosition, HL_FLOAT);
haplink.registerParam(2, &motorEnable, HL_INT32);
haplink.registerParam(3, &ledBrightness, HL_UINT8);
```

##### `registerTelemetry()`
```cpp
bool registerTelemetry(uint8_t id, void* address, HL_DataType type)
```

Register a variable for **sending to the host** as telemetry.

**Parameters**:
- `id`: Unique identifier (0-255) - must match Python side
- `address`: Pointer to the variable
- `type`: Data type

**Returns**: 
- `true` if successful
- `false` if registry is full (max 32 telemetry variables)

**Example**:
```cpp
float currentPosition = 0.0;
float currentVelocity = 0.0;
int32_t encoderCount = 0;

haplink.registerTelemetry(1, &currentPosition, HL_FLOAT);
haplink.registerTelemetry(2, &currentVelocity, HL_FLOAT);
haplink.registerTelemetry(3, &encoderCount, HL_INT32);
```

---

#### Communication

##### `update()`
```cpp
void update()
```

Process incoming packets from the host. **Call this in your `loop()` function**.

This method:
- Reads available serial data
- Parses incoming packets
- Validates checksums
- Updates registered parameters automatically

**Example**:
```cpp
void loop() {
    haplink.update();  // Process commands
    // Your code here
}
```

##### `sendTelemetry()`
```cpp
bool sendTelemetry(uint8_t id)
```

Send a single telemetry variable to the host.

**Parameters**:
- `id`: ID of the telemetry variable to send

**Returns**: 
- `true` if successful
- `false` if ID not found

**Example**:
```cpp
void loop() {
    haplink.update();
    
    // Update sensor values
    position = readEncoder();
    velocity = calculateVelocity();
    
    // Send specific telemetry
    haplink.sendTelemetry(1);  // Send position
    haplink.sendTelemetry(2);  // Send velocity
    
    delay(10);
}
```

##### `sendAllTelemetry()`
```cpp
void sendAllTelemetry()
```

Send all registered telemetry variables to the host.

**Example**:
```cpp
void loop() {
    haplink.update();
    
    // Update all sensor values
    updateSensors();
    
    // Send everything at once
    haplink.sendAllTelemetry();
    
    delay(10);
}
```

##### `connectionAlive()`
```cpp
bool connectionAlive()
```

Check if the host connection is active.

**Returns**: 
- `true` if packets received within timeout period
- `false` if no recent communication

**Example**:
```cpp
void loop() {
    haplink.update();
    
    if (haplink.connectionAlive()) {
        // Normal operation
        runMotorControl();
    } else {
        // Safety: stop motors if connection lost
        stopMotors();
    }
}
```

---

### Data Types

Use these type constants when registering variables:

| Constant    | C/C++ Type | Size    | Range                          |
|-------------|------------|---------|--------------------------------|
| `HL_UINT8`  | `uint8_t`  | 1 byte  | 0 to 255                       |
| `HL_INT16`  | `int16_t`  | 2 bytes | -32,768 to 32,767              |
| `HL_INT32`  | `int32_t`  | 4 bytes | -2,147,483,648 to 2,147,483,647|
| `HL_FLOAT`  | `float`    | 4 bytes | ±3.4e38 (7 decimal digits)     |
| `HL_DOUBLE` | `double`   | 8 bytes | ±1.7e308 (15 decimal digits)   |

**Note**: On Arduino, `double` is often the same as `float` (4 bytes). Check your platform documentation.

---

## Usage Examples

### Example 1: Motor Position Control

```cpp
#include <haplink.h>

Haplink haplink;

// Control variables
float targetPosition = 0.0;   // Set by host
float currentPosition = 0.0;  // Sent to host
float motorPWM = 0.0;         // Internal

void setup() {
    Serial.begin(115200);
    haplink.begin(Serial);
    
    // Register variables
    haplink.registerParam(1, &targetPosition, HL_FLOAT);
    haplink.registerTelemetry(1, &currentPosition, HL_FLOAT);
    
    pinMode(9, OUTPUT);  // Motor PWM pin
}

void loop() {
    haplink.update();
    
    // Read encoder
    currentPosition = readEncoder();
    
    // Simple P controller
    float error = targetPosition - currentPosition;
    motorPWM = constrain(error * 50.0, -255, 255);
    
    // Drive motor
    analogWrite(9, abs(motorPWM));
    
    // Send feedback
    haplink.sendTelemetry(1);
    
    delay(10);
}

float readEncoder() {
    // Your encoder reading code
    return 0.0;
}
```

### Example 2: Multi-Sensor Data Streaming

```cpp
#include <haplink.h>

Haplink haplink;

// Sensor data
float temperature = 0.0;
float pressure = 0.0;
float humidity = 0.0;
int32_t timestamp = 0;

void setup() {
    Serial.begin(115200);
    haplink.begin(Serial);
    
    // Register all sensors as telemetry
    haplink.registerTelemetry(1, &temperature, HL_FLOAT);
    haplink.registerTelemetry(2, &pressure, HL_FLOAT);
    haplink.registerTelemetry(3, &humidity, HL_FLOAT);
    haplink.registerTelemetry(4, &timestamp, HL_INT32);
}

void loop() {
    haplink.update();
    
    // Read sensors
    temperature = readTemperature();
    pressure = readPressure();
    humidity = readHumidity();
    timestamp = millis();
    
    // Send all data
    haplink.sendAllTelemetry();
    
    delay(100);  // 10 Hz
}
```

### Example 3: Multiple Parameters with Safety

```cpp
#include <haplink.h>

Haplink haplink;

// Parameters (host can write)
float speedSetpoint = 0.0;
int32_t enableMotor = 0;
uint8_t controlMode = 0;

// Telemetry (sent to host)
float actualSpeed = 0.0;
float motorCurrent = 0.0;

void setup() {
    Serial.begin(115200);
    haplink.begin(Serial, 500);  // 500ms timeout
    
    // Register parameters
    haplink.registerParam(1, &speedSetpoint, HL_FLOAT);
    haplink.registerParam(2, &enableMotor, HL_INT32);
    haplink.registerParam(3, &controlMode, HL_UINT8);
    
    // Register telemetry
    haplink.registerTelemetry(1, &actualSpeed, HL_FLOAT);
    haplink.registerTelemetry(2, &motorCurrent, HL_FLOAT);
}

void loop() {
    haplink.update();
    
    // Safety check
    if (haplink.connectionAlive() && enableMotor) {
        // Run motor control
        runMotor(speedSetpoint);
    } else {
        // Safety: stop if disconnected or disabled
        stopMotor();
    }
    
    // Read sensors
    actualSpeed = readSpeed();
    motorCurrent = readCurrent();
    
    // Send status
    haplink.sendAllTelemetry();
    
    delay(10);
}
```

### Example 4: Using Multiple Serial Ports

```cpp
#include <haplink.h>

Haplink haplink;
float motorSpeed = 0.0;

void setup() {
    // Serial for debugging
    Serial.begin(9600);
    Serial.println("Starting Haplink on Serial1...");
    
    // Serial1 for Haplink communication
    Serial1.begin(115200);
    haplink.begin(Serial1);
    
    haplink.registerParam(1, &motorSpeed, HL_FLOAT);
}

void loop() {
    haplink.update();
    
    // Debug output on Serial
    Serial.print("Motor speed: ");
    Serial.println(motorSpeed);
    
    delay(100);
}
```

---

## Advanced Topics

### Variable Binding

When you register a variable, Haplink stores a **pointer** to it. This means:

1. **Direct Memory Access**: Changes are immediate (no copying)
2. **Thread Safety**: Be careful with interrupts
3. **Scope**: Variables must remain in scope (use global variables or class members)

```cpp
// GOOD: Global variable
float globalSpeed = 0.0;

void setup() {
    haplink.registerParam(1, &globalSpeed, HL_FLOAT);
}

// BAD: Local variable goes out of scope
void badExample() {
    float localSpeed = 0.0;  // Dies when function returns!
    haplink.registerParam(1, &localSpeed, HL_FLOAT);  // Danger!
}
```

### Update Rate Considerations

**Recommended**: Call `update()` as fast as possible, send telemetry at your desired rate.

```cpp
unsigned long lastTelemetry = 0;

void loop() {
    haplink.update();  // Fast: check for commands
    
    // Your fast control loop
    fastControlCode();
    
    // Send telemetry at 50 Hz
    if (millis() - lastTelemetry >= 20) {
        haplink.sendAllTelemetry();
        lastTelemetry = millis();
    }
}
```

### Memory Usage

- **RAM per parameter**: ~8 bytes (pointer + metadata)
- **RAM per telemetry**: ~8 bytes
- **Maximum**: 32 params + 32 telemetry = ~512 bytes
- **Stack**: 13 bytes for packet buffer

Total overhead: Less than 1 KB on most systems.

### Serial Port Configuration

**Recommended Settings**:
- **Baud Rate**: 115200 (default)
- **Higher Rates**: 230400 or 500000 for very high-bandwidth applications
- **Lower Rates**: 57600 or 9600 if experiencing communication issues

```cpp
Serial.begin(230400);  // High-speed communication
haplink.begin(Serial);
```

---

## Troubleshooting

### Variables Not Updating

**Symptom**: Host sends parameters, but Arduino variables don't change.

**Solutions**:
1. Ensure `update()` is called in `loop()`
2. Verify IDs match between firmware and Python
3. Check data types match (e.g., both use `HL_FLOAT`)
4. Use serial monitor to verify Arduino is receiving data

### Telemetry Not Received

**Symptom**: Python receives `None` for telemetry values.

**Solutions**:
1. Call `sendTelemetry()` or `sendAllTelemetry()` in Arduino
2. Verify IDs match
3. Check baud rates match on both sides
4. Ensure Arduino has power and USB is connected

### Checksum Errors

**Symptom**: Packets are dropped or invalid.

**Solutions**:
1. Check USB cable quality
2. Reduce baud rate
3. Add decoupling capacitors to Arduino power
4. Keep USB cable short (< 2 meters)

### Connection Timeout

**Symptom**: `connectionAlive()` returns false.

**Solutions**:
1. Increase timeout: `haplink.begin(Serial, 2000);`
2. Ensure host is sending commands regularly
3. Check USB connection stability

---

## Protocol Details

For complete protocol specification including packet structure, data encoding, and checksums, see the [main repository README](../README.md#protocol-specification).

---

## See Also

- **[Python Client Documentation](../python/README.md)** - Host-side library
- **[Main README](../README.md)** - Project overview and examples
- **[Examples](../python/examples/)** - Complete working examples

---

## License

MIT License - see [LICENSE](../LICENSE) for details.

---

## Support

- **Issues**: [GitHub Issues](https://github.com/ConnorMcKelvey/Haplink/issues)
- **Email**: ConnorMcKelvey@utexas.edu
