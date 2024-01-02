"""
Simple assembler for ARM-v6 to generate opcodes

Diamino 2023
"""

R0 = 0
R1 = 1
R2 = 2
R3 = 3
R4 = 4
R5 = 5
R6 = 6
R7 = 7
R8 = 8
R9 = 9
R10 = 10
R11 = 11
R12 = 12
R13 = 13
R14 = 14
R15 = 15
SP = R13
LR = R14
PC = R15

SYSM_MSP = 8


def opcodeADC(rdn: int, rm: int) -> bytes:
    opcode = (0b0100000101 << 6) | ((rm & 0x7) << 3) | (rdn & 0x7)
    return opcode.to_bytes(2, 'little')


def opcodeADDT2(rdn: int, imm8: int) -> bytes:
    opcode = (0b00110 << 11) | ((rdn & 0x7) << 8) | (imm8 & 0xff)
    return opcode.to_bytes(2, 'little')


def opcodeADR(rd: int, imm8: int) -> bytes:
    opcode = (0b10100 << 11) | ((rd & 0x7) << 8) | (imm8 & 0xff)
    return opcode.to_bytes(2, 'little')


def opcodeBIC(rdn: int, rm: int) -> bytes:
    opcode = (0b0100001110 << 6) | ((rm & 0x7) << 3) | (rdn & 0x7)
    return opcode.to_bytes(2, 'little')


def opcodeBX(rm: int) -> bytes:
    opcode = (0b010001110 << 7) | ((rm & 0xf) << 3)
    return opcode.to_bytes(2, 'little')


def opcodeLDM(rn: int, registers: tuple[int, ...]) -> bytes:
    register_list = 0
    for i in registers:
        register_list |= 1 << i
    opcode = (0b11001 << 11) | ((rn & 0x7) << 8) | (register_list & 0xff)
    return opcode.to_bytes(2, 'little')


def opcodeLDRBimm(rt: int, rn: int, imm5: int) -> bytes:
    opcode = (0b01111 << 11) | ((imm5 & 0x1f) << 6) | ((rn & 0x7) << 3) | (rt & 0x7)
    return opcode.to_bytes(2, 'little')


def opcodeLSRimm(rd: int, rm: int, imm5: int) -> bytes:
    opcode = (0b00001 << 11) | ((imm5 & 0x1f) << 6) | ((rm & 0x7) << 3) | (rd & 0x7)
    return opcode.to_bytes(2, 'little')


def opcodeMSR(spec_reg: int, rn: int) -> bytes:
    opcode = (0b10001000 << 24) | ((spec_reg & 0xff) << 16) | (0b111100111000 << 4) | (rn & 0xf)
    return opcode.to_bytes(4, 'little')


def opcodeNEG(rd: int, rn: int) -> bytes:
    return opcodeRSB(rd, rn)


def opcodePOP(registers: tuple[int, ...]) -> bytes:
    register_list = 0
    for i in registers:
        register_list |= 1 << i
    p = (register_list >> 15) & 1
    opcode = (0b1011110 << 9) | (p << 8) | (register_list & 0xff)
    return opcode.to_bytes(2, 'little')


def opcodeRSB(rd: int, rn: int) -> bytes:
    opcode = (0b0100001001 << 6) | ((rn & 0x7) << 3) | (rd & 0x7)
    return opcode.to_bytes(2, 'little')


def opcodeSTM(rn: int, registers: tuple[int, ...]) -> bytes:
    register_list = 0
    for i in registers:
        register_list |= 1 << i
    opcode = (0b11000 << 11) | ((rn & 0x7) << 8) | (register_list & 0xff)
    return opcode.to_bytes(2, 'little')


def opcodeSTRreg(rt: int, rn: int, rm: int) -> bytes:
    opcode = (0b0101000 << 9) | ((rm & 0x7) << 6) | ((rn & 0x7) << 3) | (rt & 0x7)
    return opcode.to_bytes(2, 'little')


def opcodeSUBT2(rdn: int, imm8: int) -> bytes:
    opcode = (0b00111 << 11) | ((rdn & 0x7) << 8) | (imm8 & 0xff)
    return opcode.to_bytes(2, 'little')


def opcodeUXTB(rd: int, rm: int) -> bytes:
    opcode = (0b1011001011 << 6) | ((rm & 0x7) << 3) | (rd & 0x7)
    return opcode.to_bytes(2, 'little')
