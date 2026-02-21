#ifndef HAPLINK_TYPES_H
#define HAPLINK_TYPES_H

#include <stdint.h>

typedef struct HL_Packet{
    uint8_t header;
    uint8_t packetType;
    uint8_t id;
    uint8_t dataType;
    uint8_t data[8];
    uint8_t checksum;
} HL_Packet;

// tells how to interpret the data field of the packet
enum HL_DataType : uint8_t {
    HL_UINT8  = 1,
    HL_INT16  = 2,
    HL_INT32  = 3,
    HL_FLOAT  = 4,
    HL_DOUBLE = 5
};

// tells us what type of packet we are sending
enum HL_PacketType : uint8_t {
    HL_PACKET_PARAM_WRITE = 0xA1,
    HL_PACKET_PARAM_READ  = 0xA2,
    HL_PACKET_TELEMETRY   = 0xB1,
    HL_PACKET_HEARTBEAT   = 0xC1
};

// This struct is used to bind a parameter in the code to an ID that can be used to read/write that parameter via serial communication.
struct HL_ParamBinding {
    uint8_t id; //what is sent in the packet to identify this parameter
    void*   address; //pointer to the variable in the code that this ID corresponds to
    HL_DataType type; //tells us how to interpret the data field of the packet when reading/writing this parameter
};

// This struct is used to bind a telemetry variable in the code to an ID that can be used to send that variable via serial communication.
struct HL_TelemetryBinding {
    uint8_t id; //what is sent in the packet to identify this telemetry variable
    void*   address; //pointer to the variable in the code that this ID corresponds to
    HL_DataType type;
};

#endif