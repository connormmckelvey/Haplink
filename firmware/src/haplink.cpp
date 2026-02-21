#include "haplink.h"

//init the haplink object, resets internal states and stores serial port
void Haplink::begin(Stream &serialPort, uint32_t connectionTimeoutMs){
    packetReady = false;
    paramCount = 0;
    telemetryCount = 0;
    paramCount = 0;
    serial = &serialPort;
    CONNECTION_TIMEOUT_MS = connectionTimeoutMs;
    lastPacketTime = millis();
}

bool Haplink::registerParam(uint8_t id,void* address, HL_DataType type){
    if(paramCount < MAX_PARAMS)
    {
        paramRegistry[paramCount].id = id;
        paramRegistry[paramCount].address = address;
        paramRegistry[paramCount].type = type;
        paramCount++;
        return true;
    }
    return false; //registry full
}

bool Haplink::registerTelemetry(uint8_t id,void* address, HL_DataType type){
    if(telemetryCount < MAX_TELEMETRY)
    {
        telemetryRegistry[telemetryCount].id = id;
        telemetryRegistry[telemetryCount].address = address;
        telemetryRegistry[telemetryCount].type = type;
        telemetryCount++;
        return true;
    }
    return false; //registry full
}

void Haplink::update(){
    while(serial->available())
    {
        processIncomingByte(serial->read());
    }
}

//internal methods
void Haplink::processIncomingByte(uint8_t byte)
{
    if (rxIndex == 0)
    {
        // Waiting for start byte
        if (byte == START_BYTE)
        {
            rxBuffer[rxIndex++] = byte;
        }
        return;
    }

    rxBuffer[rxIndex++] = byte;

    if (rxIndex >= PACKET_SIZE)
    {
        // Full packet received
        HL_Packet packet;

        memcpy(&packet, rxBuffer, PACKET_SIZE);

        if (validatePacket(packet))
        {
            handlePacket(packet);
            lastPacketTime = millis();
        }

        rxIndex = 0; // Reset for next packet
    }
}

bool Haplink::validatePacket(const HL_Packet& packet)
{
    // Check header
    if (packet.header != START_BYTE)
        return false;

    // Check checksum
    return computeChecksum(packet) == packet.checksum;
}

uint8_t Haplink::computeChecksum(const HL_Packet& packet)
{
    uint8_t sum = 0;
    sum ^= packet.packetType;
    sum ^= packet.id;
    sum ^= packet.dataType;
    for (int i = 0; i < 8; i++)
    {
        sum ^= packet.data[i];
    }
    return sum;
}

void Haplink::handlePacket(const HL_Packet& packet)
{
    switch (packet.packetType)
    {
    case HL_PACKET_PARAM_WRITE:
        writeParameter(packet.id, packet.data, static_cast<HL_DataType>(packet.dataType));
        break;
    
    default:
        break;
    }
}

void Haplink::writeParameter(uint8_t id, const uint8_t* payload, HL_DataType type)
{
    for (int i = 0; i < paramCount; i++)
    {
        if (paramRegistry[i].id == id)
        {
            uint8_t size = 0;
            switch (type)
            {
            case HL_UINT8:
                size = sizeof(uint8_t);
                break;
            case HL_INT16:
                size = sizeof(int16_t);
                break;
            case HL_INT32:
                size = sizeof(int32_t);
                break;
            case HL_FLOAT:
                size = sizeof(float);
                break;
            case HL_DOUBLE:
                size = sizeof(double);
                break;
            default:
                return; // Invalid type
            }
            safeWrite(paramRegistry[i].address, const_cast<uint8_t*>(payload), size);
            return;
        }
    }
}

void Haplink::safeWrite(void* dest,
                        const uint8_t* src,
                        uint8_t size)
{
    noInterrupts();
    memcpy(dest, src, size);
    interrupts();
}

void Haplink::safeRead(uint8_t* dest, const void* src, uint8_t size)
{
    noInterrupts();
    memcpy(dest, src, size);
    interrupts();
}

bool Haplink::sendTelemetry(uint8_t id)
{
    for (uint8_t i = 0; i < telemetryCount; i++)
    {
        if (telemetryRegistry[i].id == id)
        {
            HL_Packet packet;

            packet.header = START_BYTE;
            packet.packetType = HL_PACKET_TELEMETRY;
            packet.id = id;
            packet.dataType = telemetryRegistry[i].type;

            // Determine size
            uint8_t size = 0;
            switch (telemetryRegistry[i].type)
            {
                case HL_UINT8:  size = sizeof(uint8_t); break;
                case HL_INT16:  size = sizeof(int16_t); break;
                case HL_INT32:  size = sizeof(int32_t); break;
                case HL_FLOAT:  size = sizeof(float); break;
                case HL_DOUBLE: size = sizeof(double); break;
                default: return false;
            }

            memset(packet.data, 0, 8);
            safeRead(packet.data, telemetryRegistry[i].address, size);

            // Compute checksum
            packet.checksum = computeChecksum(packet);

            // Send packet
            serial->write((uint8_t*)&packet, sizeof(HL_Packet));
            return true;
        }
    }

    return false; // ID not found
}

void Haplink::sendAllTelemetry(){
    for (int16_t i = 0; i < telemetryCount; i++)
    {
        sendTelemetry(telemetryRegistry[i].id);
    }
}

bool Haplink::connectionAlive()
{
    return (millis() - lastPacketTime) < CONNECTION_TIMEOUT_MS; // Consider connection alive if a packet was received in the last second
}