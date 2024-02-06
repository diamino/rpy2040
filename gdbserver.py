'''
RPy2040 GDB server
'''
import socket
import select
import queue
import threading
from functools import partial
from typing import Optional
import binascii
import logging
from rpy2040.rpy2040 import Rp2040, loadbin

LOGGING_LEVEL = logging.ERROR

HOST = "127.0.0.1"
PORT = 3333
FILENAME = "./examples/binaries/uart/hello_uart/hello_uart.bin"

STOP_REPLY_TRAP = "S05"

logger = logging.getLogger(__name__)

rp = Rp2040()
send_queue = queue.Queue()
rsock, ssock = socket.socketpair()  # Socket pair to signal main thread


def encode_hex(value: int, length: int = 4) -> str:
    return binascii.b2a_hex(value.to_bytes(length, 'little')).decode('utf-8')


def decode_hex(hexstr: str) -> int:
    return int.from_bytes(binascii.a2b_hex(hexstr), 'little')


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
        # Set thread
        response = 'OK'
    elif packet_data[0] == 'q':
        # Query
        if packet_data.startswith('qSupported:'):
            response = 'PacketSize=4000'
        elif packet_data == 'qAttached':
            response = '1'
    elif packet_data[0] == '?':
        # Query halt reason
        response = 'S05'
    elif packet_data[0] == 'g':
        # Read registers
        reg_strings = [encode_hex(r) for r in rp.registers]
        reg_strings.append(encode_hex(rp.apsr))
        response = ''.join(reg_strings)
    elif packet_data[0] == 'G':
        # Write registers
        reg_strings = [packet_data[1+(8*i):9+(8*i)] for i in range(17)]
        for i, v in enumerate(reg_strings[:16]):
            rp.registers[i] = decode_hex(v)
        rp.apsr = decode_hex(reg_strings[16])
        response = 'OK'
    elif packet_data[0] == 'm':
        # Read memory
        addr_str, length_str = packet_data[1:].split(',')
        addr = int(addr_str, 16)
        length = int(length_str)
        response = ''
        for i in range(length):
            response += f"{rp.mpu.read_uint8(addr + i):02x}"
    elif packet_data[0] == 'M':
        # Write memory
        addr_length_str, value_str = packet_data[1:].split(':')
        addr_str, length_str = addr_length_str.split(',')
        addr = int(addr_str, 16)
        length = int(length_str)
        value = decode_hex(value_str)
        rp.mpu.write(addr, value, length)
        response = 'OK'
    elif packet_data[0] == 'v':
        if packet_data == 'vCont?':
            response = 'vCont;c;C;s;S'
        elif packet_data.startswith('vCont;s'):
            rp.execute_instruction()
            reg_strings = [f"{i:02x}:{encode_hex(r)}" for i, r in enumerate(rp.registers)]
            reg_strings.append(f"{16:02x}:{encode_hex(rp.apsr)}")
            response = f"T05{';'.join(reg_strings)};reason:trace;"
        elif packet_data.startswith('vCont;c'):
            execute_thread = threading.Thread(target=rp.execute, daemon=True)
            execute_thread.start()
            response = 'OK'
    return gdb_response(response)


def handle_packet(data: bytes) -> Optional[bytes]:
    dollar = data.find(b'$')
    hash = data.find(b'#')
    if (hash < dollar) | (hash != (len(data) - 3)):
        logger.debug("Ignoring GDB command!")
        return None
    packet_data = data[dollar + 1: hash]
    checksum = int(data[hash + 1:], 16)
    if checksum != gdb_checksum(packet_data):
        logger.debug("Checksum invalid!")
        return b'-'
    else:
        return b'+' + handle_gdb_message(packet_data.decode('utf-8')).encode('utf-8')


def on_break_callback(reason: int):
    rp.on_break_default(reason)
    if reason == 190:  # Not sure if this always works...
        rp.pc = rp.pc_previous
    response = gdb_response(STOP_REPLY_TRAP)
    send_queue.put(response)
    ssock.send(b'\x00')


rp.on_break = on_break_callback


def main():
    import argparse

    logging.basicConfig(level=LOGGING_LEVEL)

    parser = argparse.ArgumentParser(description='RPy2040-gdb - a RP2040 emulator written in Python (with GDB stub)')

    base16 = partial(int, base=16)

    parser.add_argument('filename', type=str,
                        help='The binary (.bin) file to execute in the emulator')
    parser.add_argument('-e', '--entry_point', type=base16, nargs='?', const="0x10000000", default=None,
                        help='The entry point for execution in hex format (eg. 0x10000354). Defaults to 0x10000000 if no bootrom is loaded.')  # noqa: E501
    parser.add_argument('-b', '--bootrom', type=str,
                        help='The binary (.bin) file that holds the bootrom code. Defaults to bootrom.bin')
    parser.add_argument('-S', '--serial', type=str,
                        help='Use serial port for UART0. Specify serial port device (e.g /dev/ttyp1)')

    args = parser.parse_args()

    loadbin(args.filename, rp.flash)

    if args.bootrom:
        loadbin(args.bootrom, rp.rom)
        rp.init_from_bootrom()

    if args.entry_point:
        rp.pc = args.entry_point

    if args.serial:
        rp.mpu.regions['uart0'].init_serial(serial_port=args.serial)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(">>> RPy2040 GDB server <<<")
        try:
            while True:
                print("Waiting for connection...")
                gdb_conn, addr = s.accept()
                with gdb_conn:
                    print(f"Connected by {addr}")
                    connection_open = True
                    while connection_open:
                        rlist, _, _ = select.select([gdb_conn, rsock], [], [])
                        for ready_socket in rlist:
                            if ready_socket is gdb_conn:
                                data = gdb_conn.recv(4096)
                                if not data:
                                    connection_open = False
                                logger.debug(f"> {data}")
                                response = handle_packet(data)
                                if response:
                                    logger.debug(f"< {response}")
                                    gdb_conn.sendall(response)
                            else:
                                # Signal from other thread
                                rsock.recv(1)  # Dump the signal mark
                                # Send the data.
                                gdb_conn.sendall(send_queue.get().encode('utf-8'))
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
