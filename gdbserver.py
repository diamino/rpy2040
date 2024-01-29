'''
RPy2040 GDB server
'''
import socket
from typing import Optional
import binascii
from rpy2040.rpy2040 import Rp2040, loadbin

DEBUG = True
HOST = "127.0.0.1"
PORT = 3333
FILENAME = "./examples/binaries/uart/hello_uart/hello_uart.bin"

rp = Rp2040()


def gdb_checksum(packet_data: bytes) -> int:
    checksum = 0
    for b in packet_data:
        checksum = (checksum + b) % 256
    return checksum


def gdb_response(value: str) -> str:
    return f"${value}#{gdb_checksum(value.encode('utf-8')):02x}"


def handle_gdb_message(packet_data: str) -> str:
    response = ''
    if packet_data == 'Hg0':
        response = 'OK'
    elif packet_data[0] == 'q':
        if packet_data.startswith('qSupported:'):
            response = 'PacketSize=4000'
        elif packet_data == 'qAttached':
            response = '1'
    elif packet_data[0] == '?':
        response = 'S05'
    elif packet_data[0] == 'g':
        reg_strings = [binascii.b2a_hex(r.to_bytes(4, 'little')).decode('utf-8') for r in rp.registers]
        reg_strings.append(binascii.b2a_hex(rp.apsr.to_bytes(4, 'little')).decode('utf-8'))
        response = ''.join(reg_strings)
    elif packet_data[0] == 'm':
        addr_str, length_str = packet_data[1:].split(',')
        addr = int(addr_str, 16)
        length = int(length_str)
        response = ''
        for i in range(length):
            response += f"{rp.mpu.read_uint8(addr + i):02x}"
    return gdb_response(response)


def handle_packet(data: bytes) -> Optional[bytes]:
    dollar = data.find(b'$')
    hash = data.find(b'#')
    if (hash < dollar) | (hash != (len(data) - 3)):
        if DEBUG:
            print("Ignoring GDB command!")
        return None
    packet_data = data[dollar + 1: hash]
    checksum = int(data[hash + 1:], 16)
    if checksum != gdb_checksum(packet_data):
        if DEBUG:
            print("Checksum invalid!")
        return b'-'
    else:
        return b'+' + handle_gdb_message(packet_data.decode('utf-8')).encode('utf-8')


def main():
    import argparse
    from functools import partial

    parser = argparse.ArgumentParser(description='RPy2040-gdb - a RP2040 emulator written in Python (with GDB stub)')

    base16 = partial(int, base=16)

    parser.add_argument('filename', type=str,
                        help='The binary (.bin) file to execute in the emulator')
    parser.add_argument('-e', '--entry_point', type=base16, nargs='?', const="0x10000000", default=None,
                        help='The entry point for execution in hex format (eg. 0x10000354). Defaults to 0x10000000 if no bootrom is loaded.')  # noqa: E501
    parser.add_argument('-b', '--bootrom', type=str,
                        help='The binary (.bin) file that holds the bootrom code. Defaults to bootrom.bin')

    args = parser.parse_args()

    loadbin(args.filename, rp.flash)

    if args.bootrom:
        loadbin(args.bootrom, rp.rom)
        rp.init_from_bootrom()

    if args.entry_point:
        rp.pc = args.entry_point

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(">>> RPy2040 GDB server <<<")
        try:
            while True:
                print("Waiting for connection...")
                conn, addr = s.accept()
                with conn:
                    print(f"Connected by {addr}")
                    while True:
                        data = conn.recv(4096)
                        if not data:
                            break
                        if DEBUG:
                            print(f"{data=}")
                        response = handle_packet(data)
                        if response:
                            if DEBUG:
                                print(f"{response=}")
                            conn.sendall(response)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
