"""
Simple assembler for ARM-v6 to generate opcodes

Diamino 2023
"""


def opcodeADDT2(rdn: int, imm8: int) -> bytes:
    opcode = (0b00110 << 11) | ((rdn & 0x7) << 8) | (imm8 & 0xFF)
    return opcode.to_bytes(2, 'little')


def opcodeLDRBimm(rt: int, rn: int, imm5: int) -> bytes:
    opcode = (0b01111 << 11) | ((imm5 & 0x1f) << 6) | ((rn & 0x7) << 3) | (rt & 0x7)
    return opcode.to_bytes(2, 'little')


def opcodeNEG(rd: int, rn: int) -> bytes:
    return opcodeRSB(rd, rn)


def opcodeRSB(rd: int, rn: int) -> bytes:
    opcode = (0b0100001001 << 6) | ((rn & 0x7) << 3) | (rd & 0x7)
    return opcode.to_bytes(2, 'little')


def opcodeSUBT2(rdn: int, imm8: int) -> bytes:
    opcode = (0b00111 << 11) | ((rdn & 0x7) << 8) | (imm8 & 0xFF)
    return opcode.to_bytes(2, 'little')
