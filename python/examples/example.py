"""
Simple example demonstrating Haplink usage.
"""

from haplink import Haplink, DataType
import time

# Connect to device
haplink = Haplink('COM5', baudrate=115200)
haplink.connect()

# Register device variables (IDs must match Arduino sketch)
haplink.register_param(1, 'target_position', DataType.FLOAT)
haplink.register_telemetry(1, 'current_position', DataType.FLOAT)
haplink.register_telemetry(2, 'current_velocity', DataType.FLOAT)

# Run for 10 seconds
start_time = time.time()
target = 0.0
direction = 1

while time.time() - start_time < 10.0:
    # Receive telemetry from device
    haplink.update()
    
    # Get current state
    position = haplink.get_telemetry('current_position')
    velocity = haplink.get_telemetry('current_velocity')
    
    # Move target back and forth
    target += direction * 0.01
    if target > 1.0:
        direction = -1
    elif target < 0.0:
        direction = 1
    
    # Send new target
    haplink.set_param('target_position', target)
    
    # Display
    print(f"Target: {target:.3f}  |  Position: {position}  |  Velocity: {velocity}")
    time.sleep(0.1)

# Cleanup
haplink.disconnect()
