import sys
import os
import time
from struct import unpack
import serial
from serial.tools import list_ports

from haplink import DataType, PacketType

# ANSI Color Codes for beautiful terminal styling
CLR_HEADER    = "\033[95m"
CLR_BLUE      = "\033[94m"
CLR_CYAN      = "\033[96m"
CLR_GREEN     = "\033[92m"
CLR_YELLOW    = "\033[93m"
CLR_RED       = "\033[91m"
CLR_RESET     = "\033[0m"
CLR_GRAY      = "\033[90m"
CLR_UNDERLINE = "\033[4m"

def get_ports():
    ports = list(list_ports.comports())
    return [p.device for p in ports]

def decode_payload(data: bytes, data_type_val: int):
    try:
        # Find matching DataType
        dt = None
        for item in DataType:
            if item.code == data_type_val:
                dt = item
                break
        
        if dt is None:
            return "Invalid DataType Code"
            
        if dt == DataType.UINT8:
            return f"{unpack('B', data[:1])[0]} (uint8)"
        elif dt == DataType.INT16:
            return f"{unpack('h', data[:2])[0]} (int16)"
        elif dt == DataType.INT32:
            return f"{unpack('i', data[:4])[0]} (int32)"
        elif dt == DataType.FLOAT:
            return f"{unpack('f', data[:4])[0]:.4f} (float)"
        elif dt == DataType.DOUBLE:
            return f"{unpack('d', data[:8])[0]:.6f} (double)"
    except Exception as e:
        return f"Decoding error: {e}"
    return "Unknown"

def compute_checksum(packet_type: int, packet_id: int, data_type: int, payload: bytes) -> int:
    checksum = 0
    checksum ^= packet_type
    checksum ^= packet_id
    checksum ^= data_type
    for byte in payload:
        checksum ^= byte
    return checksum

def print_packet(packet_bytes: bytes):
    header = packet_bytes[0]
    p_type = packet_bytes[1]
    p_id = packet_bytes[2]
    d_type = packet_bytes[3]
    payload = packet_bytes[4:12]
    checksum_received = packet_bytes[12]
    
    # Calculate checksum
    checksum_calc = compute_checksum(p_type, p_id, d_type, payload)
    checksum_valid = (checksum_calc == checksum_received)
    
    # Resolve PacketType name
    type_name = "UNKNOWN"
    for pt in PacketType:
        if pt.value == p_type:
            type_name = pt.name
            break
            
    # Resolve DataType name
    dtype_name = "UNKNOWN"
    for dt in DataType:
        if dt.code == d_type:
            dtype_name = dt.name
            break
            
    decoded_val = decode_payload(payload, d_type)
    
    # Output formatted packet
    print(f"\n{CLR_HEADER}╔══════════════════ Haplink Packet Captured ══════════════════╗{CLR_RESET}")
    
    # Raw hex layout
    hex_str = " ".join([f"{b:02X}" for b in packet_bytes])
    print(f"  {CLR_GRAY}Raw Hex:{CLR_RESET}  {hex_str}")
    
    # Break down fields
    print(f"  {CLR_BLUE}Header:{CLR_RESET}   0x{header:02X} {CLR_GREEN}(START_BYTE){CLR_RESET}")
    print(f"  {CLR_BLUE}Type:{CLR_RESET}     0x{p_type:02X} {CLR_YELLOW}({type_name}){CLR_RESET}")
    print(f"  {CLR_BLUE}Var ID:{CLR_RESET}   {p_id}")
    print(f"  {CLR_BLUE}Data Type:{CLR_RESET} 0x{d_type:02X} {CLR_YELLOW}({dtype_name}){CLR_RESET}")
    
    # Payload bytes and value
    pay_hex = " ".join([f"{b:02X}" for b in payload])
    print(f"  {CLR_BLUE}Payload:{CLR_RESET}   [{pay_hex}] ➔ {CLR_CYAN}{decoded_val}{CLR_RESET}")
    
    # Checksum verification
    if checksum_valid:
        print(f"  {CLR_BLUE}Checksum:{CLR_RESET}  0x{checksum_received:02X} {CLR_GREEN}(Valid, matches calculated 0x{checksum_calc:02X}){CLR_RESET}")
    else:
        print(f"  {CLR_BLUE}Checksum:{CLR_RESET}  0x{checksum_received:02X} {CLR_RED}(FAILED! Calculated: 0x{checksum_calc:02X}){CLR_RESET}")
        
    print(f"{CLR_HEADER}╚═════════════════════════════════════════════════════════════╝{CLR_RESET}\n")

def main():
    # Enable virtual terminal processing for Windows colors
    os.system("") 
    
    print(f"{CLR_CYAN}=== Haplink Byte-by-Byte Serial Inspector ==={CLR_RESET}")
    
    ports = get_ports()
    if not ports:
        print(f"{CLR_RED}Error: No serial ports detected! Make sure your device is connected.{CLR_RESET}")
        sys.exit(1)
        
    # Auto-detect or select port
    port = ports[0]
    if len(ports) > 1:
        print("\nAvailable COM Ports:")
        for idx, p in enumerate(ports):
            print(f"  [{idx}] {p}")
        try:
            choice = input(f"Select port [0-{len(ports)-1}] (default 0): ").strip()
            if choice:
                port = ports[int(choice)]
        except (ValueError, IndexError):
            print("Invalid selection, using default.")
            
    print(f"Opening {CLR_YELLOW}{port}{CLR_RESET} at {CLR_YELLOW}115200{CLR_RESET} baud...")
    
    try:
        ser = serial.Serial(port, 115200, timeout=0.01)
    except Exception as e:
        print(f"{CLR_RED}Failed to open port: {e}{CLR_RESET}")
        sys.exit(1)
        
    print(f"{CLR_GREEN}Port opened successfully. Listening for data... (Press Ctrl+C to exit){CLR_RESET}")
    print(f"{CLR_GRAY}Raw incoming data will stream below. Packets will be framed and decoded in real-time.{CLR_RESET}\n")
    
    # Inspector loop state
    buffer = bytearray()
    last_print_was_ascii = False
    
    try:
        while True:
            # Read all available bytes
            incoming = ser.read(100)
            if not incoming:
                time.sleep(0.001)
                continue
                
            for b in incoming:
                buffer.append(b)
                
                # We attempt to align the buffer to a packet if we have at least 13 bytes
                while len(buffer) >= 13:
                    # Look for START_BYTE (0xAA)
                    if buffer[0] == 0xAA:
                        # Candidate packet
                        candidate = bytes(buffer[:13])
                        
                        # Verify candidate checksum to ensure it's not a false positive
                        p_type = candidate[1]
                        p_id = candidate[2]
                        d_type = candidate[3]
                        payload = candidate[4:12]
                        checksum_recv = candidate[12]
                        
                        # Calculate local checksum
                        checksum_calc = compute_checksum(p_type, p_id, d_type, payload)
                        
                        # Verify if this looks like a valid packet (valid packet type and checksum)
                        # We also permit standard packet type codes 0xA1, 0xA2, 0xB1, 0xC1
                        is_type_valid = p_type in [0xA1, 0xA2, 0xB1, 0xC1]
                        is_dtype_valid = 1 <= d_type <= 5
                        
                        if is_type_valid and is_dtype_valid and (checksum_calc == checksum_recv):
                            # It's a valid packet! Print it.
                            if last_print_was_ascii:
                                print() # add newline after streaming text
                                last_print_was_ascii = False
                            print_packet(candidate)
                            # Remove the 13 packet bytes from buffer
                            buffer = buffer[13:]
                        else:
                            # Not a valid checksum/packet, so let's consume 1 byte as debug/ASCII or noise
                            first_byte = buffer[0]
                            buffer = buffer[1:]
                            # Print this single byte
                            last_print_was_ascii = handle_single_byte(first_byte, last_print_was_ascii)
                    else:
                        # Leading byte is not START_BYTE, consume and print it as debug/noise
                        first_byte = buffer[0]
                        buffer = buffer[1:]
                        last_print_was_ascii = handle_single_byte(first_byte, last_print_was_ascii)
                        
    except KeyboardInterrupt:
        print(f"\n{CLR_YELLOW}Stopping inspector...{CLR_RESET}")
    finally:
        ser.close()
        print(f"{CLR_GREEN}Port closed. Goodbye!{CLR_RESET}")

def handle_single_byte(b: int, last_print_was_ascii: bool) -> bool:
    # Printable ASCII ranges, or carriage returns/tabs
    if 32 <= b <= 126 or b in [10, 13, 9]:
        # Print directly
        char = chr(b)
        sys.stdout.write(char)
        sys.stdout.flush()
        return True
    else:
        # Print non-printable bytes in gray hex brackets
        if last_print_was_ascii:
            print() # newline
        sys.stdout.write(f"{CLR_GRAY}[0x{b:02X}]{CLR_RESET}")
        sys.stdout.flush()
        return False

if __name__ == "__main__":
    main()
