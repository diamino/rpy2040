'''
RP2040 emulator written in Python

Inspired by the rp2040js emulator by Uri Shaked (https://github.com/wokwi/rp2040js)
'''
import array
import ctypes
from typing import Iterable
from .peripherals.mpu import Mpu
from .peripherals.memory import ByteArrayMemory
from .peripherals.uart import Uart
from .peripherals.xipssi import XipSsi
from .peripherals.resets import Resets
from .peripherals.sio import Sio
from .peripherals.cortexreg import CortexRegisters

DEBUG_REGISTERS = True
DEBUG_INSTRUCTIONS = True

ROM_START = 0x00000000
ROM_SIZE = 16 * 1024  # 16kB
FLASH_START = 0x10000000
FLASH_SIZE = 16 * 1024 * 1024  # 16MB
SRAM_START = 0x20000000
SRAM_SIZE = 264 * 1024  # 264kB

# Default values for SP and PC
SP_START = 0x20041000
PC_START = 0x10000000


def loadbin(filename: str, mem: bytearray, offset: int = 0) -> None:
    with open(filename, 'rb') as fp:
        b = fp.read()
    mem[offset:len(b)+offset] = b


def sign_extend(value, no_bits_in: int) -> int:
    sign = (value >> (no_bits_in - 1)) & 1
    sign_bits = ~(~0 << (32 - no_bits_in))
    return ctypes.c_int32(((sign_bits if sign else 0) << no_bits_in) | value).value


def add_with_carry(x: int, y: int, carry_in: bool) -> tuple[int, bool, bool]:
    x &= 0xFFFFFFFF
    y &= 0xFFFFFFFF
    unsigned_sum = x + y + carry_in
    signed_sum = sign_extend(x, 32) + sign_extend(y, 32) + carry_in
    result = unsigned_sum & 0xFFFFFFFF
    carry_out = False if result == unsigned_sum else True
    overflow = False if sign_extend(result, 32) == signed_sum else True
    return (result, carry_out, overflow)


class Rp2040:

    def __init__(self):
        self.registers = array.array('l', 16*[0])
        self.apsr: int = 0
        self.pc = PC_START
        self.sp = SP_START
        self.mpu = Mpu()
        rom_region = ByteArrayMemory(ROM_START, ROM_SIZE)
        sram_region = ByteArrayMemory(SRAM_START, SRAM_SIZE)
        flash_region = ByteArrayMemory(FLASH_START, FLASH_SIZE, 0xFF)
        self.rom = rom_region.memory
        self.sram = sram_region.memory
        self.flash = flash_region.memory
        self.mpu.register_region("flash", flash_region)
        self.mpu.register_region("sram", sram_region)
        self.mpu.register_region("rom", rom_region)
        self.mpu.register_region("cortex0", CortexRegisters())
        self.mpu.register_region("sio", Sio())
        self.mpu.register_region("uart0", Uart())
        self.mpu.register_region("xip_ssi", XipSsi())
        self.mpu.register_region("resets", Resets())

    def init_from_bootrom(self):
        self.sp = self.mpu.regions["rom"].read(0)
        self.pc = self.mpu.regions["rom"].read(4) & 0xfffffffe

    @property
    def pc(self) -> int:
        return self.registers[15]

    @pc.setter
    def pc(self, value: int):
        self.registers[15] = value

    @property
    def sp(self) -> int:
        return self.registers[13]

    @sp.setter
    def sp(self, value: int):
        self.registers[13] = value

    @property
    def lr(self) -> int:
        return self.registers[14]

    @lr.setter
    def lr(self, value: int):
        self.registers[14] = value

    @property
    def apsr_n(self) -> bool:
        return bool(self.apsr & (1 << 31))

    @apsr_n.setter
    def apsr_n(self, value: bool):
        if value:
            self.apsr |= (1 << 31)
        else:
            self.apsr &= ~(1 << 31)

    @property
    def apsr_z(self) -> bool:
        return bool(self.apsr & (1 << 30))

    @apsr_z.setter
    def apsr_z(self, value: bool):
        if value:
            self.apsr |= (1 << 30)
        else:
            self.apsr &= ~(1 << 30)

    @property
    def apsr_c(self) -> bool:
        return bool(self.apsr & (1 << 29))

    @apsr_c.setter
    def apsr_c(self, value: bool):
        if value:
            self.apsr |= (1 << 29)
        else:
            self.apsr &= ~(1 << 29)

    @property
    def apsr_v(self) -> bool:
        return bool(self.apsr & (1 << 28))

    @apsr_v.setter
    def apsr_v(self, value: bool):
        if value:
            self.apsr |= (1 << 28)
        else:
            self.apsr &= ~(1 << 28)

    def str_registers(self, registers: Iterable[int] = range(16)) -> str:
        return '\t'.join([f"R[{i:02}]: {self.registers[i]:#010x}" for i in registers])

    def condition_passed(self, cond: int) -> bool:
        if (cond >> 1) == 0b000:  # EQ or NE
            result = self.apsr_z
        elif (cond >> 1) == 0b001:  # CS or CC
            result = self.apsr_c
        elif (cond >> 1) == 0b010:  # MI or PL
            result = self.apsr_n
        elif (cond >> 1) == 0b011:  # VS or VC
            result = self.apsr_v
        elif (cond >> 1) == 0b100:  # HI or LS
            result = self.apsr_c and not self.apsr_z
        elif (cond >> 1) == 0b101:  # GE or LT
            result = (self.apsr_n == self.apsr_v)
        elif (cond >> 1) == 0b110:  # GT or LE
            result = (self.apsr_n == self.apsr_v) and not self.apsr_z
        else:  # AL
            result = True
        if (cond & 1) and cond != 0b1111:
            return not result
        else:
            return result

    def execute_instruction(self) -> None:
        if DEBUG_REGISTERS:
            print(f"\nPC: {self.pc:#010x}\tSP: {self.sp:#010x}\tAPSR: {self.apsr:#010x}")
        # TODO: Opcode loading can be sped up by referencing the XIP flash directly
        opcode = self.mpu.read_uint16(self.pc)
        self.pc += 2
        opcode2 = 0
        if (opcode >> 11) == 0b11110:
            # instr_loc = self.pc - FLASH_START
            # opcode2 = int.from_bytes(self.flash[instr_loc:instr_loc+2], "little")
            opcode2 = self.mpu.read_uint16(self.pc)
            self.pc += 2

        if DEBUG_REGISTERS:
            print(self.str_registers(registers=range(4)))
            print(self.str_registers(registers=range(4, 8)))
            print(self.str_registers(registers=range(8, 12)))
            print(self.str_registers(registers=range(12, 16)))
            print(f"Current opcode is [{opcode:04x}]")
        # ADC
        if (opcode >> 6) == 0b0100000101:
            print("  ADC instruction...")
            m = (opcode >> 3) & 0x07
            dn = opcode & 0x7
            # TODO: special case for SP register (13)
            print(f"    Add R[{m}] to R[{dn}] with carry")
            result, c, v = add_with_carry(self.registers[dn], self.registers[m], self.apsr_c)
            self.registers[dn] = result
            self.apsr_n = bool(result & (1 << 31))
            self.apsr_z = bool(result == 0)
            self.apsr_c = c
            self.apsr_v = v
        # ADD (immediate) T2
        elif (opcode >> 11) == 0b00110:
            print("  ADD (immediate) T2 instruction...")
            dn = ((opcode >> 8) & 0x7)
            imm = opcode & 0xFF
            print(f"    Add {imm:#x} to R[{dn}] ...")
            result, c, v = add_with_carry(self.registers[dn], imm, False)
            self.registers[dn] = result
            self.apsr_n = bool(result & (1 << 31))
            self.apsr_z = bool(result == 0)
            self.apsr_c = c
            self.apsr_v = v
        # ADD (register) T2
        elif (opcode >> 8) == 0b01000100:
            print("  ADD (register) T2 instruction...")
            dn = ((opcode >> 4) & 0x08) | (opcode & 0x7)
            m = (opcode >> 3) & 0xF
            # TODO: special case for SP register (13)
            print(f"    Source R[{m}]\tDestination R[{dn}]")
            self.registers[dn] = self.registers[m] + self.registers[dn]
        # ADR
        elif (opcode >> 11) == 0b10100:
            print("  ADR instruction...")
            d = (opcode >> 8) & 0x7
            imm32 = (opcode & 0xff) << 2
            print(f"    Value [{imm32}]+PC \tDestination R[{d}]")
            self.registers[d] = (self.pc & 0xfffffffc) + imm32
        # B T1
        elif (opcode >> 12) == 0b1101:
            print("  B T1 instruction...")
            imm8 = opcode & 0xff
            cond = (opcode >> 8) & 0xf
            imm32 = sign_extend(imm8 << 1, 9)
            print(f"    {imm32=}")
            if self.condition_passed(cond):
                print(f"    Branch to: {(self.pc + imm32 + 2):#010x}")
                self.pc += imm32 + 2
            else:
                print(f"    Condition False. Will NOT branch to: {(self.pc + imm32 + 2):#010x}")
        # B T2
        elif (opcode >> 11) == 0b11100:
            print("  B T2 instruction...")
            imm11 = opcode & 0x7ff
            imm32 = sign_extend(imm11 << 1, 12)
            print(f"    {imm32=}")
            print(f"    Branch to: {(self.pc + imm32 + 2):#010x}")
            self.pc += imm32 + 2
        # BIC
        elif (opcode >> 6) == 0b0100001110:
            print("  BIC instruction...")
            dn = opcode & 0x7
            m = (opcode >> 3) & 0x7
            result = self.registers[dn] & ~self.registers[m]
            self.registers[dn] = result
            self.apsr_n = bool(result & (1 << 31))
            self.apsr_z = bool(result == 0)
        # BL
        elif ((opcode >> 11) == 0b11110) and ((opcode2 >> 14) == 0b11):
            print("  BL instruction...")
            imm10 = opcode & 0x3ff
            imm11 = opcode2 & 0x7ff
            j1 = bool(opcode2 & 0x2000)
            j2 = bool(opcode2 & 0x800)
            s = bool(opcode & 0x400)
            i1 = not (j1 ^ s)
            i2 = not (j2 ^ s)
            print(f"    {j1=} {j2=} {s=} {i1=} {i2=} {imm10=} {imm11=}")
            imm23 = int(i1) << 23 | int(i2) << 22 | imm10 << 12 | imm11 << 1
            imm32 = sign_extend(imm23, 23)
            print(f"    {imm32=}")
            print(f"    Branch to: {(self.pc + imm32):#010x}")
            self.lr = self.pc | 0x1
            self.pc += imm32
        # BLX
        elif (opcode >> 7) == 0b010001111:
            print("  BLX instruction...")
            m = (opcode >> 3) & 0xf
            address = self.registers[m] & 0xfffffffe
            print(f"    Branch to: {address:#010x}")
            self.lr = self.pc | 0x1
            self.pc = address
        # BX
        elif (opcode >> 7) == 0b010001110:
            print("  BX instruction...")
            m = (opcode >> 3) & 0xf
            # TODO: handle exception cases
            address = self.registers[m] & 0xfffffffe
            print(f"    Branch to: {address:#010x}")
            self.pc = address
        # CMP (immediate)
        elif (opcode >> 11) == 0b00101:
            print("  CMP (immediate) instruction...")
            n = ((opcode >> 8) & 0x7)
            imm = opcode & 0xFF
            print(f"    Compare R[{n}] with {imm:#x}...")
            result, c, v = add_with_carry(self.registers[n], ~imm, True)
            self.apsr_n = bool(result & (1 << 31))
            self.apsr_z = bool(result == 0)
            self.apsr_c = c
            self.apsr_v = v
        # CMP (register) T1
        elif (opcode >> 6) == 0b0100001010:
            print("  CMP (register) T1 instruction...")
            n = ((opcode >> 3) & 0x7)
            m = opcode & 0x7
            print(f"    Compare R[{n}] with R[{m}]...")
            result, c, v = add_with_carry(self.registers[n], ~self.registers[m], True)
            self.apsr_n = bool(result & (1 << 31))
            self.apsr_z = bool(result == 0)
            self.apsr_c = c
            self.apsr_v = v
        # LDM
        elif (opcode >> 11) == 0b11001:
            print("  LDM instruction...")
            n = (opcode >> 8) & 0x7
            register_list = opcode & 0xff
            address = self.registers[n]
            wback = not ((register_list >> n) & 1)
            print(f"    Destination registers[{register_list:#b}]\tSource address [{address:#010x}]")
            for i in range(8):
                if (register_list >> i) & 1:
                    self.registers[i] = self.mpu.read_uint32(address)
                    address += 4
            if wback:
                self.registers[n] += 4 * register_list.bit_count()
        # LDR (immediate)
        elif (opcode >> 11) == 0b01101:
            print("  LDR (immediate) instruction...")
            n = (opcode >> 3) & 0x7
            t = opcode & 0x7
            imm = ((opcode >> 6) & 0x1F) << 2
            address = self.registers[n] + imm
            print(f"    Destination R[{t}]\tSource address [{address:#010x}]")
            self.registers[t] = self.mpu.read_uint32(address)
        # LDR (literal)
        elif (opcode >> 11) == 0b01001:
            print("  LDR (literal) instruction...")
            t = (opcode >> 8) & 0x7
            imm = (opcode & 0xFF) << 2
            base = (self.pc + 2) & 0xfffffffc
            address = base + imm
            print(f"    Destination R[{t}]\tSource address [{address:#010x}]")
            self.registers[t] = self.mpu.read_uint32(address)
        # LDRB (immediate)
        elif (opcode >> 11) == 0b01111:
            print("  LDRB (immediate) instruction...")
            imm5 = (opcode >> 6) & 0x1F
            n = (opcode >> 3) & 0x7
            t = opcode & 0x7
            address = self.registers[n] + imm5
            print(f"    Destination R[{t}]\tSource address [{address:#010x}]")
            self.registers[t] = self.mpu.read_uint8(address)
        # LDRSH (register)
        elif (opcode >> 9) == 0b0101111:
            print("  LDRSH (register) instruction...")
            m = (opcode >> 6) & 0x7
            n = (opcode >> 3) & 0x7
            t = opcode & 0x7
            address = self.registers[n] + self.registers[m]
            print(f"    Destination R[{t}]\tSource address [{address:#010x}]")
            self.registers[t] = self.mpu.read_uint16(address)
        # LSLS (immediate)
        elif (opcode >> 11) == 0b00000:
            print("  LSLS (immediate) instruction...")
            m = (opcode >> 3) & 0x07
            d = opcode & 0x07
            shift_n = (opcode >> 6) & 0x1F
            print(f"    Source R[{m}]\tDestination R[{d}]\tShift amount [{shift_n}]")
            result = self.registers[m] << shift_n
            self.registers[d] = result & 0xFFFFFFFF
            self.apsr_n = bool(result & (1 << 31))
            self.apsr_z = bool(result == 0)
            if shift_n > 0:
                self.apsr_c = bool(result & (1 << 32))
        # LSLS (register)
        elif (opcode >> 6) == 0b0100000010:
            print("  LSLS (register) instruction...")
            m = (opcode >> 3) & 0x7
            d = opcode & 0x7
            shift_n = self.registers[m] & 0xFF
            print(f"    Source and destination R[{d}]\tShift amount [{shift_n}]")
            result = self.registers[d] << shift_n
            self.registers[d] = result & 0xFFFFFFFF
            self.apsr_n = bool(result & (1 << 31))
            self.apsr_z = bool(result == 0)
            if shift_n > 0:
                self.apsr_c = bool(result & (1 << 32))
        # LSR (immediate)
        elif (opcode >> 11) == 0b00001:
            print("  LSR (immediate) instruction...")
            m = (opcode >> 3) & 0x07
            d = opcode & 0x07
            imm5 = (opcode >> 6) & 0x1F
            shift_n = imm5 if imm5 != 0 else 32
            print(f"    Source R[{m}]\tDestination R[{d}]\tShift amount [{shift_n}]")
            result = self.registers[m] >> shift_n
            self.registers[d] = result & 0xFFFFFFFF
            self.apsr_n = bool(result & (1 << 31))
            self.apsr_z = bool(result == 0)
            self.apsr_c = bool((self.registers[m] >> (shift_n - 1)) & 1)
        # MOV (immediate)
        elif (opcode >> 11) == 0b00100:
            print("  MOV (immediate) instruction...")
            d = (opcode >> 8) & 0x07
            value = opcode & 0xFF
            print(f"    Destination register is [{d}]\tValue is [{value}]")
            self.registers[d] = value
            self.apsr_n = bool(value & (1 << 31))
            self.apsr_z = bool(value == 0)
        # MOV (register)
        elif (opcode >> 8) == 0b01000110:
            print("  MOV (register) instruction...")
            d = ((opcode >> 4) & 0x08) | (opcode & 0x7)
            m = (opcode >> 3) & 0xF
            print(f"    Source R[{m}]\tDestination R[{d}]")
            result = self.registers[m]
            self.registers[d] = result
            if d != 15:
                self.apsr_n = bool(result & (1 << 31))
                self.apsr_z = bool(result == 0)
        # MSR
        elif ((opcode >> 5) == 0b11110011100) and ((opcode2 >> 14) == 0b10):
            print("  MSR instruction...")
            n = opcode & 0xf
            sysm = opcode2 & 0xff
            print(f"    Source R[{n}]\tDestination SYSm[{sysm}]")
            # TODO: other registers like APSR, PRIMASK, etc
            # TODO: privileged and unprivileged mode
            if sysm >> 3 == 1:  # SP
                if sysm & 0x7 == 0:  # MSP = SP_main
                    self.sp = self.registers[n] & 0xfffffffc
        # POP
        elif (opcode >> 9) == 0b1011110:
            print("  POP instruction...")
            p = (opcode >> 8) & 0x1
            register_list = (p << 15) | opcode & 0xff
            address = self.sp
            for i in range(8):
                if (register_list & (1 << i)):
                    self.registers[i] = self.mpu.read_uint32(address)
                    address += 4
            if p:
                self.pc = self.mpu.read_uint32(address) & 0xfffffffe
            self.sp += 4 * register_list.bit_count()
        # PUSH
        elif (opcode >> 9) == 0b1011010:
            print("  PUSH instruction...")
            bitcount = (opcode & 0x1FF).bit_count()
            address = self.sp - 4 * bitcount
            for i in range(8):
                if (opcode & (1 << i)):
                    self.mpu.write_uint32(address, self.registers[i])
                    address += 4
            if (opcode & (1 << 8)):  # 'M'-bit -> push LR register
                self.mpu.write_uint32(address, self.registers[14])
            self.sp -= 4 * bitcount
        # RSB / NEG
        elif (opcode >> 6) == 0b0100001001:
            print("  RSB / NEG instruction...")
            n = ((opcode >> 3) & 0x7)
            d = opcode & 0x7
            print(f"    Subtract R[{n}] from 0 and store in R[{d}]...")
            result, c, v = add_with_carry(~self.registers[n], 0, True)
            self.registers[d] = result
            self.apsr_n = bool(result & (1 << 31))
            self.apsr_z = bool(result == 0)
            self.apsr_c = c
            self.apsr_v = v
        # STM
        elif (opcode >> 11) == 0b11000:
            print("  STM instruction...")
            n = (opcode >> 8) & 0x7
            register_list = opcode & 0xff
            address = self.registers[n]
            print(f"    Source registers[{register_list:#b}]\tDestination address [{address:#010x}]")
            for i in range(8):
                if (register_list >> i) & 1:
                    self.mpu.write_uint32(address, self.registers[i])
                    address += 4
            self.registers[n] += 4 * register_list.bit_count()
        # STR immediate (T1)
        elif (opcode >> 11) == 0b01100:
            print("  STR (immediate) instruction...")
            n = (opcode >> 3) & 0x7
            t = opcode & 0x7
            imm = ((opcode >> 6) & 0x1F) << 2
            address = self.registers[n] + imm
            print(f"    Source R[{t}]\tDestination address [{address:#010x}]")
            self.mpu.write_uint32(address, self.registers[t])
        # STR register
        elif (opcode >> 9) == 0b0101000:
            print("  STR (register) instruction...")
            m = (opcode >> 6) & 0x7
            n = (opcode >> 3) & 0x7
            t = opcode & 0x7
            address = self.registers[n] + self.registers[m]
            print(f"    Source R[{t}]\tDestination address [{address:#010x}]")
            self.mpu.write_uint32(address, self.registers[t])
        # SUB (immediate) T2
        elif (opcode >> 11) == 0b00111:
            print("  SUB (immediate) T2 instruction...")
            dn = ((opcode >> 8) & 0x7)
            imm = opcode & 0xFF
            print(f"    Subtract {imm:#x} from R[{dn}]...")
            result, c, v = add_with_carry(self.registers[dn], ~imm, True)
            self.registers[dn] = result
            self.apsr_n = bool(result & (1 << 31))
            self.apsr_z = bool(result == 0)
            self.apsr_c = c
            self.apsr_v = v
        # SUB (SP minus immediate)
        elif (opcode >> 7) == 0b101100001:
            print("  SUB (SP minus immediate) instruction...")
            imm32 = (opcode & 0x7F) << 2
            print(f"    Subtract {imm32:#x} from SP...")
            result, c, v = add_with_carry(self.sp, ~imm32, True)
            self.sp = result
        # TST immediate (T1)
        elif (opcode >> 6) == 0b0100001000:
            print("  TST instruction...")
            n = opcode & 0x7
            m = (opcode >> 3) & 0x7
            result = self.registers[n] & self.registers[m]
            self.apsr_n = bool(result & (1 << 31))
            self.apsr_z = bool(result == 0)
            print(f"  APSR: {self.apsr:08x}")
        # UXTB
        elif (opcode >> 6) == 0b1011001011:
            print("  UXTB instruction...")
            d = opcode & 0x7
            m = (opcode >> 3) & 0x7
            self.registers[d] = self.registers[m] & 0xFF
        else:
            print(" Instruction not implemented!!!!")
            raise NotImplementedError
