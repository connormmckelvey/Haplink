#ifndef HAPLINK_H
#define HAPLINK_H

#include <stdint.h>
#include <Arduino.h>
#include "haplink_types.h"

class Haplink
{
    public:
        void begin(Stream &serialPort,uint32_t connectionTimeoutMs = 1000);
        bool registerParam(uint8_t id,void* address, HL_DataType type);
        bool registerTelemetry(uint8_t id, void* address, HL_DataType type);
        void update();
        bool sendTelemetry(uint8_t id);
        void sendAllTelemetry();
        bool connectionAlive();
    private:

    static const uint8_t MAX_PARAMS = 32; //max amt of params dictated by size of param is 1 byte in the packet structure
    static const uint8_t MAX_TELEMETRY = 32; //max amt of telemetry variables dictated by size of param is 1 byte in the packet structure
    static const uint8_t PACKET_SIZE = 13; // 1 byte header, 1 byte packet type, 1 byte id, 1 byte data type, 8 bytes data, 1 byte checksum
    static const uint8_t START_BYTE = 0xAA; //arbitrary start byte to indicate the start of a packet, can be any value but should be unique to avoid confusion with data bytes
    uint32_t CONNECTION_TIMEOUT_MS = 1000; //if we haven't received a packet in this amount of time, consider the connection dead 

    // ===== Serial Interface =====
    Stream* serial; //pointer to the serial port object (e.g., Serial, Serial1, etc.) that is passed in during begin()

    // ===== Registries =====
    HL_ParamBinding paramRegistry[MAX_PARAMS]; //list of binded params 
    HL_TelemetryBinding telemetryRegistry[MAX_TELEMETRY]; //list of binded telemetry variables

    uint8_t paramCount; 
    uint8_t telemetryCount;

    // ===== Parser State =====
    uint8_t rxBuffer[PACKET_SIZE];
    uint8_t rxIndex;
    bool packetReady;

    // ===== Connection Tracking =====
    unsigned long lastPacketTime;

    // ===== Internal Methods =====
    void processIncomingByte(uint8_t byte);
    bool validatePacket(const HL_Packet& packet);
    void handlePacket(const HL_Packet& packet);

    void writeParameter(uint8_t id, const uint8_t* payload, HL_DataType type);
    void safeWrite(void* dest, const uint8_t* src, uint8_t size);
    void safeRead(uint8_t* dest, const void* src, uint8_t size);

    uint8_t computeChecksum(const HL_Packet& packet);

};

#endif