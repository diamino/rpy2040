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

# Conditions
EQ = 0b0000
NE = 0b0001
CS = 0b0010
CC = 0b0011
MI = 0b0100
PL = 0b0101
VS = 0b0110
VC = 0b0111
HI = 0b1000
LS = 0b1001
GE = 0b1010
LT = 0b1011
GT = 0b1100
LE = 0b1101
AL = 0b1110


def opcodeADC(rdn: int, rm: int) -> bytes:
    opcode = (0b0100000101 << 6) | ((rm & 0x7) << 3) | (rdn & 0x7)
    return opcode.to_bytes(2, 'little')


def opcodeADDimmT1(rd: int, rn: int, imm3: int) -> bytes:
    opcode = (0b0001110 << 9) | ((imm3 & 0x7) << 6) | ((rn & 0x7) << 3) | (rd & 0x7)
    return opcode.to_bytes(2, 'little')


def opcodeADDimmT2(rdn: int, imm8: int) -> bytes:
    opcode = (0b00110 << 11) | ((rdn & 0x7) << 8) | (imm8 & 0xff)
    return opcode.to_bytes(2, 'little')


def opcodeADDregT1(rd: int, rn: int, rm: int) -> bytes:
    opcode = (0b0001100 << 9) | ((rm & 0x7) << 6) | ((rn & 0x7) << 3) | (rd & 0x7)
    return opcode.to_bytes(2, 'little')


def opcodeADDregT2(rdn: int, rm: int) -> bytes:
    opcode = (0b01000100 << 8) | ((rdn & 8) << 4) | ((rm & 0xf) << 3) | (rdn & 0x7)
    return opcode.to_bytes(2, 'little')


def opcodeADDSPimmT2(imm7: int) -> bytes:
    opcode = (0b101100000 << 7) | (imm7 & 0x7f)
    return opcode.to_bytes(2, 'little')


def opcodeADR(rd: int, imm8: int) -> bytes:
    opcode = (0b10100 << 11) | ((rd & 0x7) << 8) | (imm8 & 0xff)
    return opcode.to_bytes(2, 'little')


def opcodeAND(rdn: int, rm: int) -> bytes:
    opcode = (0b0100000000 << 6) | ((rm & 0x7) << 3) | (rdn & 0x7)
    return opcode.to_bytes(2, 'little')


def opcodeBT1(cond: int, imm8: int) -> bytes:
    opcode = (0b1101 << 12) | ((cond & 0xf) << 8) | (imm8 & 0xff)
    return opcode.to_bytes(2, 'little')


def opcodeBT2(imm11: int) -> bytes:
    opcode = (0b11100 << 11) | (imm11 & 0x7ff)
    return opcode.to_bytes(2, 'little')


def opcodeBIC(rdn: int, rm: int) -> bytes:
    opcode = (0b0100001110 << 6) | ((rm & 0x7) << 3) | (rdn & 0x7)
    return opcode.to_bytes(2, 'little')


def opcodeBL(imm32: int) -> bytes:
    imm10 = (imm32 >> 12) & 0x3ff
    imm11 = (imm32 >> 1) & 0x7ff
    s = (imm32 >> 31) & 1
    i1 = (imm32 >> 32) & 1
    j1 = ~(i1 ^ s) & 1
    i2 = (imm32 >> 32) & 1
    j2 = ~(i2 ^ s) & 1
    opcode = (0b1101 << 28) | (j1 << 29) | (j2 << 27) | (imm11 << 16) | (0b11110 << 11) | (s << 10) | imm10
    return opcode.to_bytes(4, 'little')


def opcodeBLX(rm: int) -> bytes:
    opcode = (0b010001111 << 7) | ((rm & 0xf) << 3)
    return opcode.to_bytes(2, 'little')


def opcodeBX(rm: int) -> bytes:
    opcode = (0b010001110 << 7) | ((rm & 0xf) << 3)
    return opcode.to_bytes(2, 'little')


def opcodeCMPimm(rn: int, imm8: int) -> bytes:
    opcode = (0b00101 << 11) | ((rn & 0x7) << 8) | (imm8 & 0xff)
    return opcode.to_bytes(2, 'little')


def opcodeCMPregT1(rn: int, rm: int) -> bytes:
    opcode = (0b0100001010 << 6) | ((rm & 0x7) << 3) | (rn & 0x7)
    return opcode.to_bytes(2, 'little')


def opcodeEOR(rdn: int, rm: int) -> bytes:
    opcode = (0b0100000001 << 6) | ((rm & 0x7) << 3) | (rdn & 0x7)
    return opcode.to_bytes(2, 'little')


def opcodeLDM(rn: int, registers: tuple[int, ...]) -> bytes:
    register_list = 0
    for i in registers:
        register_list |= 1 << i
    opcode = (0b11001 << 11) | ((rn & 0x7) << 8) | (register_list & 0xff)
    return opcode.to_bytes(2, 'little')


def opcodeLDRimmT1(rt: int, rn: int, imm5: int) -> bytes:
    opcode = (0b01101 << 11) | ((imm5 & 0x1f) << 6) | ((rn & 0x7) << 3) | (rt & 0x7)
    return opcode.to_bytes(2, 'little')


def opcodeLDRimmT2(rt: int, imm8: int) -> bytes:
    opcode = (0b10011 << 11) | ((rt & 0x7) << 8) | (imm8 & 0xff)
    return opcode.to_bytes(2, 'little')


def opcodeLDRlit(rt: int, imm8: int) -> bytes:
    opcode = (0b01001 << 11) | ((rt & 0x7) << 8) | (imm8 & 0xff)
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


def opcodeMVN(rd: int, rm: int) -> bytes:
    opcode = (0b0100001111 << 6) | ((rm & 0x7) << 3) | (rd & 0x7)
    return opcode.to_bytes(2, 'little')


def opcodeNEG(rd: int, rn: int) -> bytes:
    return opcodeRSB(rd, rn)


def opcodeORR(rdn: int, rm: int) -> bytes:
    opcode = (0b0100001100 << 6) | ((rm & 0x7) << 3) | (rdn & 0x7)
    return opcode.to_bytes(2, 'little')


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


def opcodeSTRimmT2(rt: int, imm8: int) -> bytes:
    opcode = (0b10010 << 11) | ((rt & 0x7) << 8) | (imm8 & 0xff)
    return opcode.to_bytes(2, 'little')


def opcodeSTRreg(rt: int, rn: int, rm: int) -> bytes:
    opcode = (0b0101000 << 9) | ((rm & 0x7) << 6) | ((rn & 0x7) << 3) | (rt & 0x7)
    return opcode.to_bytes(2, 'little')


def opcodeSUBT1(rd: int, rn: int, imm3: int) -> bytes:
    opcode = (0b0001111 << 9) | ((imm3 & 0x7) << 6) | ((rn & 0x7) << 3) | (rd & 0x7)
    return opcode.to_bytes(2, 'little')


def opcodeSUBT2(rdn: int, imm8: int) -> bytes:
    opcode = (0b00111 << 11) | ((rdn & 0x7) << 8) | (imm8 & 0xff)
    return opcode.to_bytes(2, 'little')


def opcodeSUBreg(rd: int, rn: int, rm: int) -> bytes:
    opcode = (0b0001101 << 9) | ((rm & 0x7) << 6) | ((rn & 0x7) << 3) | (rd & 0x7)
    return opcode.to_bytes(2, 'little')


def opcodeSUBSP(imm7: int) -> bytes:
    opcode = (0b101100001 << 7) | (imm7 & 0x7f)
    return opcode.to_bytes(2, 'little')


def opcodeUXTB(rd: int, rm: int) -> bytes:
    opcode = (0b1011001011 << 6) | ((rm & 0x7) << 3) | (rd & 0x7)
    return opcode.to_bytes(2, 'little')
