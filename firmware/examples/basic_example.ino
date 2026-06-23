/*
  Basic Example for Haplink

  This sketch demonstrates how to set up Haplink on a microcontroller,
  register variables for parameter control and telemetry streaming,
  and handle bidirectional serial communication in a non-blocking loop.

  It matches the Python example client ('example.py') by exposing:
    - 1 Parameter: target_position (ID 1, FLOAT)
    - 2 Telemetry variables: current_position (ID 1, FLOAT), current_velocity (ID 2, FLOAT)

  The loop simulates a basic mechanical response where the 'current_position'
  smoothly tracks the 'target_position' received from the host.
*/

#include <haplink.h>

// Instantiate Haplink
Haplink haplink;

// Variables to expose over Haplink
float targetPosition = 0.0;    // Parameter (writable by host)
float currentPosition = 0.0;   // Telemetry (readable by host)
float currentVelocity = 0.0;   // Telemetry (readable by host)

// Timing control for physics update and telemetry streaming (100 Hz)
unsigned long lastUpdate = 0;
const unsigned long updateIntervalMs = 10; 

void setup() {
    // Start serial communication at 115200 baud
    Serial.begin(115200);
    
    // Initialize Haplink using the Serial interface
    haplink.begin(Serial);

    // Register parameter (ID: 1, writable by host)
    haplink.registerParam(1, &targetPosition, HL_FLOAT);

    // Register telemetry variables (IDs must be unique within telemetry)
    haplink.registerTelemetry(1, &currentPosition, HL_FLOAT);
    haplink.registerTelemetry(2, &currentVelocity, HL_FLOAT);
}

void loop() {
    // Process any incoming packets from the host and update registered parameter variables
    haplink.update();

    unsigned long now = millis();
    if (now - lastUpdate >= updateIntervalMs) {
        float dt = (now - lastUpdate) / 1000.0; // Delta time in seconds
        lastUpdate = now;

        // Simulate physical tracking: currentPosition moves towards targetPosition
        float error = targetPosition - currentPosition;
        
        // Simple proportional tracking velocity
        currentVelocity = error * 5.0; // Kp gain of 5.0
        currentPosition += currentVelocity * dt;

        // Stream all registered telemetry variables back to the host
        haplink.sendAllTelemetry();
    }
}
