'''
RP2040 emulator written in Python

Inspired by the rp2040js emulator by Uri Shaked (https://github.com/wokwi/rp2040js)
'''
import array
import ctypes
import logging
from typing import Iterable, Callable
from .peripherals.mpu import Mpu
from .peripherals.memory import ByteArrayMemory
from .peripherals.uart import Uart
from .peripherals.xipssi import XipSsi
from .peripherals.resets import Resets
from .peripherals.sio import Sio
from .peripherals.cortexreg import CortexRegisters
from .peripherals.xosc import Xosc
from .peripherals.clocks import Clocks
from .peripherals.pll import Pll, PLL_USB_BASE

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

logger = logging.getLogger("rpy2040")


def loadbin(filename: str, mem: bytearray, offset: int = 0) -> None:
    with open(filename, 'rb') as fp:
        b = fp.read()
    mem[offset:len(b)+offset] = b


def sign_extend(value: int, no_bits_in: int) -> int:
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
        self.on_break: Callable[[int], None] = self.on_break_default
        self.stopped = False
        self.stop_reason = 0
        self.registers = array.array('l', 16*[0])
        self.xpsr: int = 0
        self.epsr_t = True
        self.primask_pm: bool = False
        self.pc = PC_START
        self.pc_previous = PC_START
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
        self.mpu.register_region("xosc", Xosc())
        self.mpu.register_region("clocks", Clocks())
        self.mpu.register_region("pll_sys", Pll())
        self.mpu.register_region("pll_usb", Pll(base_address=PLL_USB_BASE))

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
    def apsr(self) -> int:
        return self.xpsr & 0xf0000000

    @apsr.setter
    def apsr(self, value: int):
        self.xpsr &= ~0xf0000000
        self.xpsr |= (value & 0xf0000000)

    @property
    def apsr_n(self) -> bool:
        return bool(self.xpsr & (1 << 31))

    @apsr_n.setter
    def apsr_n(self, value: bool):
        if value:
            self.xpsr |= (1 << 31)
        else:
            self.xpsr &= ~(1 << 31)

    @property
    def apsr_z(self) -> bool:
        return bool(self.xpsr & (1 << 30))

    @apsr_z.setter
    def apsr_z(self, value: bool):
        if value:
            self.xpsr |= (1 << 30)
        else:
            self.xpsr &= ~(1 << 30)

    @property
    def apsr_c(self) -> bool:
        return bool(self.xpsr & (1 << 29))

    @apsr_c.setter
    def apsr_c(self, value: bool):
        if value:
            self.xpsr |= (1 << 29)
        else:
            self.xpsr &= ~(1 << 29)

    @property
    def apsr_v(self) -> bool:
        return bool(self.xpsr & (1 << 28))

    @apsr_v.setter
    def apsr_v(self, value: bool):
        if value:
            self.xpsr |= (1 << 28)
        else:
            self.xpsr &= ~(1 << 28)

    @property
    def ipsr(self) -> int:
        return self.xpsr & 0x3f

    @ipsr.setter
    def ipsr(self, value: int):
        self.xpsr &= ~0x3f
        self.xpsr |= (value & 0x3f)

    @property
    def epsr_t(self) -> bool:
        return bool(self.xpsr & (1 << 24))

    @epsr_t.setter
    def epsr_t(self, value: bool):
        if value:
            self.xpsr |= (1 << 24)
        else:
            self.xpsr &= ~(1 << 24)

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
        logger.info("")
        logger.info(f"PC: {self.pc:#010x}\tSP: {self.sp:#010x}\txPSR: {self.xpsr:#010x}")
        # TODO: Opcode loading can be sped up by referencing the XIP flash directly
        opcode = self.mpu.read_uint16(self.pc)
        self.pc_previous = self.pc
        self.pc += 2
        opcode2 = 0
        if (opcode >> 12) == 0b1111:
            # instr_loc = self.pc - FLASH_START
            # opcode2 = int.from_bytes(self.flash[instr_loc:instr_loc+2], "little")
            opcode2 = self.mpu.read_uint16(self.pc)
            self.pc += 2

        logger.info(self.str_registers(registers=range(4)))
        logger.info(self.str_registers(registers=range(4, 8)))
        logger.info(self.str_registers(registers=range(8, 12)))
        logger.info(self.str_registers(registers=range(12, 16)))

        # ADC
        if (opcode >> 6) == 0b0100000101:
            logger.debug("  ADC instruction...")
            m = (opcode >> 3) & 0x07
            dn = opcode & 0x7
            # TODO: special case for SP register (13)
            logger.debug(f"    Add R[{m}] to R[{dn}] with carry")
            result, c, v = add_with_carry(self.registers[dn], self.registers[m], self.apsr_c)
            self.registers[dn] = result
            self.apsr_n = bool(result & (1 << 31))
            self.apsr_z = bool(result == 0)
            self.apsr_c = c
            self.apsr_v = v
        # ADD (immediate) T1
        elif (opcode >> 9) == 0b0001110:
            logger.debug("  ADD (immediate) T1 instruction...")
            imm = ((opcode >> 6) & 0x7)
            n = ((opcode >> 3) & 0x7)
            d = opcode & 0x7
            logger.debug(f"    Add {imm:#x} to R[{n}]\tDestination: R[{d}] ...")
            result, c, v = add_with_carry(self.registers[n], imm, False)
            self.registers[d] = result
            self.apsr_n = bool(result & (1 << 31))
            self.apsr_z = bool(result == 0)
            self.apsr_c = c
            self.apsr_v = v
        # ADD (immediate) T2
        elif (opcode >> 11) == 0b00110:
            logger.debug("  ADD (immediate) T2 instruction...")
            dn = ((opcode >> 8) & 0x7)
            imm = opcode & 0xFF
            logger.debug(f"    Add {imm:#x} to R[{dn}] ...")
            result, c, v = add_with_carry(self.registers[dn], imm, False)
            self.registers[dn] = result
            self.apsr_n = bool(result & (1 << 31))
            self.apsr_z = bool(result == 0)
            self.apsr_c = c
            self.apsr_v = v
        # ADD (register) T1
        elif (opcode >> 9) == 0b0001100:
            logger.debug("  ADD (register) T1 instruction...")
            m = ((opcode >> 6) & 0x7)
            n = ((opcode >> 3) & 0x7)
            d = opcode & 0x7
            logger.debug(f"    Add R[{n}] to R[{m}]\tDestination: R[{d}] ...")
            result, c, v = add_with_carry(self.registers[n], self.registers[m], False)
            self.registers[d] = result
            if d != 15:
                self.apsr_n = bool(result & (1 << 31))
                self.apsr_z = bool(result == 0)
                self.apsr_c = c
                self.apsr_v = v
        # ADD (register) T2
        elif (opcode >> 8) == 0b01000100:
            logger.debug("  ADD (register) T2 instruction...")
            dn = ((opcode >> 4) & 0x08) | (opcode & 0x7)
            m = (opcode >> 3) & 0xF
            # TODO: special case for SP register (13)
            logger.debug(f"    Source R[{m}]\tDestination R[{dn}]")
            self.registers[dn] = self.registers[m] + self.registers[dn]
        # ADD (SP plus immediate) T1
        elif (opcode >> 11) == 0b10101:
            logger.debug("  ADD (SP plus immediate) T1 instruction...")
            imm32 = (opcode & 0xFF) << 2
            d = (opcode >> 8) & 0x7
            logger.debug(f"    ADD r{d}, sp, #{imm32}...")
            result, c, v = add_with_carry(self.sp, imm32, False)
            self.registers[d] = result
        # ADD (SP plus immediate) T2
        elif (opcode >> 7) == 0b101100000:
            logger.debug("  ADD (SP plus immediate) T2 instruction...")
            imm32 = (opcode & 0x7F) << 2
            logger.debug(f"    Add {imm32:#x} to SP...")
            result, c, v = add_with_carry(self.sp, imm32, False)
            self.sp = result
        # ADR
        elif (opcode >> 11) == 0b10100:
            logger.debug("  ADR instruction...")
            d = (opcode >> 8) & 0x7
            imm32 = (opcode & 0xff) << 2
            logger.debug(f"    Value [{imm32}]+PC \tDestination R[{d}]")
            self.registers[d] = (self.pc & 0xfffffffc) + imm32
        # AND
        elif (opcode >> 6) == 0b0100000000:
            logger.debug("  AND instruction...")
            m = ((opcode >> 3) & 0x7)
            dn = opcode & 0x7
            logger.debug(f"    AND r{dn}, r{m}...")
            result = self.registers[dn] & self.registers[m]
            self.registers[dn] = result
            self.apsr_n = bool(result & (1 << 31))
            self.apsr_z = bool(result == 0)
        # ASR (immediate)
        elif (opcode >> 11) == 0b00010:
            logger.debug("  ASR (immediate) instruction...")
            m = (opcode >> 3) & 0x07
            d = opcode & 0x07
            imm5 = (opcode >> 6) & 0x1F
            shift_n = imm5 if imm5 != 0 else 32
            logger.debug(f"    Source R[{m}]\tDestination R[{d}]\tShift amount [{shift_n}]")
            if shift_n < 32:
                result = sign_extend(self.registers[m] >> shift_n, 32 - shift_n)
            else:
                result = sign_extend(self.registers[m] >> 31, 1)
            self.registers[d] = result & 0xFFFFFFFF
            self.apsr_n = bool(result & (1 << 31))
            self.apsr_z = bool(result == 0)
            self.apsr_c = bool((self.registers[m] >> (shift_n - 1)) & 1)
        # B T1
        elif ((opcode >> 12) == 0b1101) and (((opcode >> 9) & 0x7) != 0b111):
            logger.debug("  B T1 instruction...")
            imm8 = opcode & 0xff
            cond = (opcode >> 8) & 0xf
            imm32 = sign_extend(imm8 << 1, 9)
            logger.debug(f"    {imm32=}")
            if self.condition_passed(cond):
                logger.debug(f"    Branch to: {(self.pc + imm32 + 2):#010x}")
                self.pc += imm32 + 2
            else:
                logger.debug(f"    Condition False. Will NOT branch to: {(self.pc + imm32 + 2):#010x}")
        # B T2
        elif (opcode >> 11) == 0b11100:
            logger.debug("  B T2 instruction...")
            imm11 = opcode & 0x7ff
            imm32 = sign_extend(imm11 << 1, 12)
            logger.debug(f"    {imm32=}")
            logger.debug(f"    Branch to: {(self.pc + imm32 + 2):#010x}")
            self.pc += imm32 + 2
        # BIC
        elif (opcode >> 6) == 0b0100001110:
            logger.debug("  BIC instruction...")
            dn = opcode & 0x7
            m = (opcode >> 3) & 0x7
            result = self.registers[dn] & ~self.registers[m]
            self.registers[dn] = result
            self.apsr_n = bool(result & (1 << 31))
            self.apsr_z = bool(result == 0)
        # BKPT
        elif (opcode >> 8) == 0b10111110:
            imm8 = opcode & 0xff
            logger.debug(" BKPT instruction...")
            self.on_break(imm8)
        # BL
        elif ((opcode >> 11) == 0b11110) and ((opcode2 >> 14) == 0b11):
            logger.debug("  BL instruction...")
            imm10 = opcode & 0x3ff
            imm11 = opcode2 & 0x7ff
            j1 = bool(opcode2 & 0x2000)
            j2 = bool(opcode2 & 0x800)
            s = bool(opcode & 0x400)
            i1 = not (j1 ^ s)
            i2 = not (j2 ^ s)
            logger.debug(f"    {j1=} {j2=} {s=} {i1=} {i2=} {imm10=} {imm11=}")
            imm23 = int(i1) << 23 | int(i2) << 22 | imm10 << 12 | imm11 << 1
            imm32 = sign_extend(imm23, 23)
            logger.debug(f"    {imm32=}")
            logger.debug(f"    Branch to: {(self.pc + imm32):#010x}")
            self.lr = self.pc | 0x1
            self.pc += imm32
        # BLX
        elif (opcode >> 7) == 0b010001111:
            logger.debug("  BLX instruction...")
            m = (opcode >> 3) & 0xf
            address = self.registers[m] & 0xfffffffe
            logger.debug(f"    Branch to: {address:#010x}")
            self.lr = self.pc | 0x1
            self.pc = address
        # BX
        elif (opcode >> 7) == 0b010001110:
            logger.debug("  BX instruction...")
            m = (opcode >> 3) & 0xf
            # TODO: handle exception cases
            address = self.registers[m] & 0xfffffffe
            logger.debug(f"    Branch to: {address:#010x}")
            self.pc = address
        # CMP (immediate)
        elif (opcode >> 11) == 0b00101:
            logger.debug("  CMP (immediate) instruction...")
            n = ((opcode >> 8) & 0x7)
            imm = opcode & 0xFF
            logger.debug(f"    Compare R[{n}] with {imm:#x}...")
            result, c, v = add_with_carry(self.registers[n], ~imm, True)
            self.apsr_n = bool(result & (1 << 31))
            self.apsr_z = bool(result == 0)
            self.apsr_c = c
            self.apsr_v = v
        # CMP (register) T1
        elif (opcode >> 6) == 0b0100001010:
            logger.debug("  CMP (register) T1 instruction...")
            m = ((opcode >> 3) & 0x7)
            n = opcode & 0x7
            logger.debug(f"    Compare R[{n}] with R[{m}]...")
            result, c, v = add_with_carry(self.registers[n], ~self.registers[m], True)
            self.apsr_n = bool(result & (1 << 31))
            self.apsr_z = bool(result == 0)
            self.apsr_c = c
            self.apsr_v = v
        # CMP (register) T2
        elif (opcode >> 8) == 0b01000101:
            logger.debug("  CMP (register) T2 instruction...")
            n = ((opcode >> 4) & 0x08) | (opcode & 0x7)
            m = (opcode >> 3) & 0xF
            # TODO: special case for SP register (13)
            logger.debug(f"    CMP r{n}, r{m}")
            result, c, v = add_with_carry(self.registers[n], ~self.registers[m], True)
            self.apsr_n = bool(result & (1 << 31))
            self.apsr_z = bool(result == 0)
            self.apsr_c = c
            self.apsr_v = v
        # CPS
        elif (opcode >> 5) == 0b10110110011:
            logger.debug("  CPS instruction...")
            im = ((opcode >> 4) & 0x1)
            effect = 'ID' if im == 1 else 'IE'
            logger.debug(f"    CPS{effect} i...")
            # TODO: only execute when in privileged mode
            self.primask_pm = bool(im)
        # DMB
        elif (opcode == 0b1111001110111111) and ((opcode2 >> 4) == 0b100011110101):
            # assert (opcode2 & 0xf) == 0b1111  # Apparently other options are used by the compiler
            logger.debug("    DMB sy")
            pass
        # EOR
        elif (opcode >> 6) == 0b0100000001:
            m = ((opcode >> 3) & 0x7)
            dn = opcode & 0x7
            logger.debug(f"    EOR r{dn}, r{m}")
            result = self.registers[dn] ^ self.registers[m]
            self.registers[dn] = result
            self.apsr_n = bool(result & (1 << 31))
            self.apsr_z = bool(result == 0)
        # LDM
        elif (opcode >> 11) == 0b11001:
            logger.debug("  LDM instruction...")
            n = (opcode >> 8) & 0x7
            register_list = opcode & 0xff
            address = self.registers[n]
            wback = not ((register_list >> n) & 1)
            logger.debug(f"    Destination registers[{register_list:#b}]\tSource address [{address:#010x}]")
            for i in range(8):
                if (register_list >> i) & 1:
                    self.registers[i] = self.mpu.read_uint32(address)
                    address += 4
            if wback:
                self.registers[n] += 4 * register_list.bit_count()
        # LDR (immediate)
        elif (opcode >> 11) == 0b01101:
            logger.debug("  LDR (immediate) instruction...")
            n = (opcode >> 3) & 0x7
            t = opcode & 0x7
            imm = ((opcode >> 6) & 0x1F) << 2
            address = self.registers[n] + imm
            logger.debug(f"    Destination R[{t}]\tSource address [{address:#010x}]")
            self.registers[t] = self.mpu.read_uint32(address)
        # LDR immediate (T2)
        elif (opcode >> 11) == 0b10011:
            logger.debug("  LDR (immediate) T2 instruction...")
            t = (opcode >> 8) & 0x7
            imm32 = (opcode & 0xff) << 2
            address = self.registers[13] + imm32
            logger.debug(f"    Source address [{address:#010x}]\tDestination R[{t}]")
            self.registers[t] = self.mpu.read_uint32(address)
        # LDR (literal)
        elif (opcode >> 11) == 0b01001:
            logger.debug("  LDR (literal) instruction...")
            t = (opcode >> 8) & 0x7
            imm = (opcode & 0xFF) << 2
            base = (self.pc + 2) & 0xfffffffc
            address = base + imm
            logger.debug(f"    Destination R[{t}]\tSource address [{address:#010x}]")
            self.registers[t] = self.mpu.read_uint32(address)
        # LDR (register)
        elif (opcode >> 9) == 0b0101100:
            logger.debug("  LDR (register) instruction...")
            m = (opcode >> 6) & 0x7
            n = (opcode >> 3) & 0x7
            t = opcode & 0x7
            address = self.registers[n] + self.registers[m]
            logger.debug(f"    LDR r{t}, [r{n}, r{m}]")
            self.registers[t] = self.mpu.read_uint32(address)
        # LDRB (immediate)
        elif (opcode >> 11) == 0b01111:
            logger.debug("  LDRB (immediate) instruction...")
            imm5 = (opcode >> 6) & 0x1F
            n = (opcode >> 3) & 0x7
            t = opcode & 0x7
            address = self.registers[n] + imm5
            logger.debug(f"    Destination R[{t}]\tSource address [{address:#010x}]")
            self.registers[t] = self.mpu.read_uint8(address)
        # LDRB (register)
        elif (opcode >> 9) == 0b0101110:
            logger.debug("  LDRB (register) instruction...")
            m = (opcode >> 6) & 0x7
            n = (opcode >> 3) & 0x7
            t = opcode & 0x7
            address = self.registers[n] + self.registers[m]
            logger.debug(f"    LRDB r{t}, [r{n}, r{m}]")
            self.registers[t] = self.mpu.read_uint8(address)
        # LDRH (immediate)
        elif (opcode >> 11) == 0b10001:
            logger.debug("  LDRH (immediate) instruction...")
            imm5 = (opcode >> 6) & 0x1F
            n = (opcode >> 3) & 0x7
            t = opcode & 0x7
            address = self.registers[n] + (imm5 << 1)
            logger.debug(f"    Destination R[{t}]\tSource address [{address:#010x}]")
            self.registers[t] = self.mpu.read_uint16(address)
        # LDRSB (register)
        elif (opcode >> 9) == 0b0101011:
            logger.debug("  LDRSB (register) instruction...")
            m = (opcode >> 6) & 0x7
            n = (opcode >> 3) & 0x7
            t = opcode & 0x7
            address = self.registers[n] + self.registers[m]
            logger.debug(f"    LRDSB r{t}, [r{n}, r{m}]")
            self.registers[t] = sign_extend(self.mpu.read_uint8(address), 8) & 0xffffffff
        # LDRSH (register)
        elif (opcode >> 9) == 0b0101111:
            logger.debug("  LDRSH (register) instruction...")
            m = (opcode >> 6) & 0x7
            n = (opcode >> 3) & 0x7
            t = opcode & 0x7
            address = self.registers[n] + self.registers[m]
            logger.debug(f"    Destination R[{t}]\tSource address [{address:#010x}]")
            self.registers[t] = self.mpu.read_uint16(address)
        # LSLS (immediate)
        elif (opcode >> 11) == 0b00000:
            logger.debug("  LSLS (immediate) instruction...")
            m = (opcode >> 3) & 0x07
            d = opcode & 0x07
            shift_n = (opcode >> 6) & 0x1F
            logger.debug(f"    Source R[{m}]\tDestination R[{d}]\tShift amount [{shift_n}]")
            result = (self.registers[m] << shift_n) & 0xffffffff
            carry = (self.registers[m] >> 32 - shift_n) & 1
            self.registers[d] = result
            if d != 15:  # This is actually MOV reg T2 encoding
                self.apsr_n = bool(result & (1 << 31))
                self.apsr_z = bool(result == 0)
                if shift_n > 0:
                    self.apsr_c = bool(carry)
        # LSLS (register)
        elif (opcode >> 6) == 0b0100000010:
            logger.debug("  LSLS (register) instruction...")
            m = (opcode >> 3) & 0x7
            d = opcode & 0x7
            shift_n = self.registers[m] & 0xFF
            logger.debug(f"    Source and destination R[{d}]\tShift amount [{shift_n}]")
            result = self.registers[d] << shift_n
            self.registers[d] = result & 0xFFFFFFFF
            self.apsr_n = bool(result & (1 << 31))
            self.apsr_z = bool(result == 0)
            if shift_n > 0:
                self.apsr_c = bool(result & (1 << 32))
        # LSR (immediate)
        elif (opcode >> 11) == 0b00001:
            logger.debug("  LSR (immediate) instruction...")
            m = (opcode >> 3) & 0x07
            d = opcode & 0x07
            imm5 = (opcode >> 6) & 0x1F
            shift_n = imm5 if imm5 != 0 else 32
            logger.debug(f"    Source R[{m}]\tDestination R[{d}]\tShift amount [{shift_n}]")
            result = self.registers[m] >> shift_n
            self.registers[d] = result & 0xFFFFFFFF
            self.apsr_n = bool(result & (1 << 31))
            self.apsr_z = bool(result == 0)
            self.apsr_c = bool((self.registers[m] >> (shift_n - 1)) & 1)
        # LSR (register)
        elif (opcode >> 6) == 0b0100000011:
            logger.debug("  LSR (register) instruction...")
            m = (opcode >> 3) & 0x07
            dn = opcode & 0x07
            shift_n = self.registers[m] & 0xff
            logger.debug(f"    LSRS r{dn}, r{m}")
            result = self.registers[dn] >> shift_n
            carry = (self.registers[dn] >> (shift_n - 1)) & 1
            self.registers[dn] = result & 0xFFFFFFFF
            self.apsr_n = bool(result & (1 << 31))
            self.apsr_z = bool(result == 0)
            self.apsr_c = bool(carry)
        # MOV (immediate)
        elif (opcode >> 11) == 0b00100:
            logger.debug("  MOV (immediate) instruction...")
            d = (opcode >> 8) & 0x07
            value = opcode & 0xFF
            logger.debug(f"    Destination register is [{d}]\tValue is [{value}]")
            self.registers[d] = value
            self.apsr_n = bool(value & (1 << 31))
            self.apsr_z = bool(value == 0)
        # MOV (register)
        elif (opcode >> 8) == 0b01000110:
            logger.debug("  MOV (register) instruction...")
            d = ((opcode >> 4) & 0x08) | (opcode & 0x7)
            m = (opcode >> 3) & 0xF
            logger.debug(f"    Source R[{m}]\tDestination R[{d}]")
            result = self.registers[m]
            if d != 15:
                self.registers[d] = result
            else:
                self.pc = result & 0xfffffffe
        # MRS
        elif (opcode == 0b1111001111101111) and ((opcode2 >> 12) == 0b1000):
            logger.debug("  MRS instruction...")
            d = (opcode2 >> 8) & 0xf
            sysm = opcode2 & 0xff
            logger.debug(f"    Source SYSm[{sysm}]\tDestination R[{d}]")
            # TODO: other registers like APSR, PRIMASK, etc
            # TODO: privileged and unprivileged mode
            self.registers[d] = 0  # Always set result register to zero
        # MSR
        elif ((opcode >> 5) == 0b11110011100) and ((opcode2 >> 14) == 0b10):
            logger.debug("  MSR instruction...")
            n = opcode & 0xf
            sysm = opcode2 & 0xff
            logger.debug(f"    Source R[{n}]\tDestination SYSm[{sysm}]")
            # TODO: other registers like APSR, PRIMASK, etc
            # TODO: privileged and unprivileged mode
            if sysm >> 3 == 1:  # SP
                if sysm & 0x7 == 0:  # MSP = SP_main
                    self.sp = self.registers[n] & 0xfffffffc
        # MUL
        elif (opcode >> 6) == 0b0100001101:
            logger.debug("  MUL instruction...")
            dm = (opcode & 0x7)
            n = (opcode >> 3) & 0x7
            logger.debug(f"    MUL r{dm}, r{n}")
            result = (self.registers[dm] * self.registers[n]) & 0xffffffff
            self.registers[dm] = result
            self.apsr_n = bool(result & (1 << 31))
            self.apsr_z = bool(result == 0)
        # MVN
        elif (opcode >> 6) == 0b0100001111:
            logger.debug("  MVN instruction...")
            m = ((opcode >> 3) & 0x7)
            d = opcode & 0x7
            logger.debug(f"    Bitwise NOT on R[{m}] and store in R[{d}]...")
            result = ~self.registers[m] & 0xffffffff
            self.registers[d] = result
            self.apsr_n = bool(result & (1 << 31))
            self.apsr_z = bool(result == 0)
        # ORR
        elif (opcode >> 6) == 0b0100001100:
            logger.debug("  ORR instruction...")
            m = ((opcode >> 3) & 0x7)
            dn = opcode & 0x7
            logger.debug(f"    ORR r{dn}, r{m}...")
            result = self.registers[dn] | self.registers[m]
            self.registers[dn] = result
            self.apsr_n = bool(result & (1 << 31))
            self.apsr_z = bool(result == 0)
        # POP
        elif (opcode >> 9) == 0b1011110:
            logger.debug("  POP instruction...")
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
            logger.debug("  PUSH instruction...")
            bitcount = (opcode & 0x1FF).bit_count()
            address = self.sp - 4 * bitcount
            for i in range(8):
                if (opcode & (1 << i)):
                    self.mpu.write_uint32(address, self.registers[i])
                    address += 4
            if (opcode & (1 << 8)):  # 'M'-bit -> push LR register
                self.mpu.write_uint32(address, self.registers[14])
            self.sp -= 4 * bitcount
        # REV
        elif (opcode >> 6) == 0b1011101000:
            logger.debug("  REV instruction...")
            m = ((opcode >> 3) & 0x7)
            d = opcode & 0x7
            logger.debug(f"    REV r{d}, r{m}...")
            value = self.registers[m]
            result = (value & 0xff) << 24
            result |= (value & 0xff00) << 8
            result |= (value & 0xff0000) >> 8
            result |= (value & 0xff000000) >> 24
            self.registers[d] = result
        # RSB / NEG
        elif (opcode >> 6) == 0b0100001001:
            logger.debug("  RSB / NEG instruction...")
            n = ((opcode >> 3) & 0x7)
            d = opcode & 0x7
            logger.debug(f"    Subtract R[{n}] from 0 and store in R[{d}]...")
            result, c, v = add_with_carry(~self.registers[n], 0, True)
            self.registers[d] = result
            self.apsr_n = bool(result & (1 << 31))
            self.apsr_z = bool(result == 0)
            self.apsr_c = c
            self.apsr_v = v
        # SBC
        elif (opcode >> 6) == 0b0100000110:
            logger.debug("  SBC instruction...")
            m = ((opcode >> 3) & 0x7)
            dn = opcode & 0x7
            logger.debug(f"    SBCS r{dn}, r{m}")
            result, c, v = add_with_carry(self.registers[dn], ~self.registers[m], self.apsr_c)
            self.registers[dn] = result
            self.apsr_n = bool(result & (1 << 31))
            self.apsr_z = bool(result == 0)
            self.apsr_c = c
            self.apsr_v = v
        # SEV
        elif opcode == 0b1011111101000000:
            pass
        # STM
        elif (opcode >> 11) == 0b11000:
            logger.debug("  STM instruction...")
            n = (opcode >> 8) & 0x7
            register_list = opcode & 0xff
            address = self.registers[n]
            logger.debug(f"    Source registers[{register_list:#b}]\tDestination address [{address:#010x}]")
            for i in range(8):
                if (register_list >> i) & 1:
                    self.mpu.write_uint32(address, self.registers[i])
                    address += 4
            self.registers[n] += 4 * register_list.bit_count()
        # STR immediate (T1)
        elif (opcode >> 11) == 0b01100:
            logger.debug("  STR (immediate) T1 instruction...")
            n = (opcode >> 3) & 0x7
            t = opcode & 0x7
            imm = ((opcode >> 6) & 0x1F) << 2
            address = self.registers[n] + imm
            logger.debug(f"    Source R[{t}]\tDestination address [{address:#010x}]")
            self.mpu.write_uint32(address, self.registers[t])
        # STR immediate (T2)
        elif (opcode >> 11) == 0b10010:
            logger.debug("  STR (immediate) T2 instruction...")
            t = (opcode >> 8) & 0x7
            imm32 = (opcode & 0xff) << 2
            address = self.registers[13] + imm32
            logger.debug(f"    Source R[{t}]\tDestination address [{address:#010x}]")
            self.mpu.write_uint32(address, self.registers[t])
        # STR register
        elif (opcode >> 9) == 0b0101000:
            logger.debug("  STR (register) instruction...")
            m = (opcode >> 6) & 0x7
            n = (opcode >> 3) & 0x7
            t = opcode & 0x7
            address = self.registers[n] + self.registers[m]
            logger.debug(f"    Source R[{t}]\tDestination address [{address:#010x}]")
            self.mpu.write_uint32(address, self.registers[t])
        # STRB immediate
        elif (opcode >> 11) == 0b01110:
            imm5 = (opcode >> 6) & 0x1f
            n = (opcode >> 3) & 0x7
            t = opcode & 0x7
            address = self.registers[n] + imm5
            logger.debug(f"    STRB r{t}, [r{n}, #{imm5}]")
            self.mpu.write(address, self.registers[t] & 0xff, num_bytes=1)
        # STRB register
        elif (opcode >> 9) == 0b0101010:
            m = (opcode >> 6) & 0x7
            n = (opcode >> 3) & 0x7
            t = opcode & 0x7
            address = self.registers[n] + self.registers[m]
            logger.debug(f"    STRB r{t}, [r{n}, r{m}]")
            self.mpu.write(address, self.registers[t] & 0xff, num_bytes=1)
        # STRH immediate
        elif (opcode >> 11) == 0b10000:
            imm = ((opcode >> 6) & 0x1f) << 1
            n = (opcode >> 3) & 0x7
            t = opcode & 0x7
            address = self.registers[n] + imm
            logger.debug(f"    STRB r{t}, [r{n}, #{imm}]")
            self.mpu.write(address, self.registers[t] & 0xffff, num_bytes=2)
        # STRH register
        elif (opcode >> 9) == 0b0101001:
            m = (opcode >> 6) & 0x7
            n = (opcode >> 3) & 0x7
            t = opcode & 0x7
            address = self.registers[n] + self.registers[m]
            logger.debug(f"    STRH r{t}, [r{n}, r{m}]")
            self.mpu.write(address, self.registers[t] & 0xffff, num_bytes=2)
        # SUB (immediate) T1
        elif (opcode >> 9) == 0b0001111:
            d = opcode & 0x7
            n = (opcode >> 3) & 0x7
            imm = (opcode >> 6) & 0x7
            logger.debug(f"    SUBS r{d}, r{n}, #{imm}")
            result, c, v = add_with_carry(self.registers[n], ~imm, True)
            self.registers[d] = result
            self.apsr_n = bool(result & (1 << 31))
            self.apsr_z = bool(result == 0)
            self.apsr_c = c
            self.apsr_v = v
        # SUB (immediate) T2
        elif (opcode >> 11) == 0b00111:
            logger.debug("  SUB (immediate) T2 instruction...")
            dn = ((opcode >> 8) & 0x7)
            imm = opcode & 0xFF
            logger.debug(f"    Subtract {imm:#x} from R[{dn}]...")
            result, c, v = add_with_carry(self.registers[dn], ~imm, True)
            self.registers[dn] = result
            self.apsr_n = bool(result & (1 << 31))
            self.apsr_z = bool(result == 0)
            self.apsr_c = c
            self.apsr_v = v
        # SUB (register) T1
        elif (opcode >> 9) == 0b0001101:
            logger.debug("  SUB (register) T1 instruction...")
            m = ((opcode >> 6) & 0x7)
            n = ((opcode >> 3) & 0x7)
            d = opcode & 0x7
            logger.debug(f"    Add R[{n}] to R[{m}]\tDestination: R[{d}] ...")
            result, c, v = add_with_carry(self.registers[n], ~self.registers[m], True)
            self.registers[d] = result
            if d != 15:
                self.apsr_n = bool(result & (1 << 31))
                self.apsr_z = bool(result == 0)
                self.apsr_c = c
                self.apsr_v = v
        # SUB (SP minus immediate)
        elif (opcode >> 7) == 0b101100001:
            logger.debug("  SUB (SP minus immediate) instruction...")
            imm32 = (opcode & 0x7F) << 2
            logger.debug(f"    Subtract {imm32:#x} from SP...")
            result, c, v = add_with_carry(self.sp, ~imm32, True)
            self.sp = result
        # SXTB
        elif (opcode >> 6) == 0b1011001001:
            logger.debug("  SXTB instruction...")
            d = opcode & 0x7
            m = (opcode >> 3) & 0x7
            self.registers[d] = sign_extend(self.registers[m] & 0xFF, 8) & 0xffffffff
        # TST immediate (T1)
        elif (opcode >> 6) == 0b0100001000:
            logger.debug("  TST instruction...")
            n = opcode & 0x7
            m = (opcode >> 3) & 0x7
            result = self.registers[n] & self.registers[m]
            self.apsr_n = bool(result & (1 << 31))
            self.apsr_z = bool(result == 0)
        # UXTB
        elif (opcode >> 6) == 0b1011001011:
            logger.debug("  UXTB instruction...")
            d = opcode & 0x7
            m = (opcode >> 3) & 0x7
            self.registers[d] = self.registers[m] & 0xFF
        # UXTH
        elif (opcode >> 6) == 0b1011001010:
            logger.debug("  UXTH instruction...")
            d = opcode & 0x7
            m = (opcode >> 3) & 0x7
            self.registers[d] = self.registers[m] & 0xFFFF
        # WFE
        elif opcode == 0b1011111100100000:
            logger.debug("    WFE")
            pass
        else:
            logger.warning(" Instruction not implemented!!!!")
            # raise NotImplementedError
            self.on_break(42)

    def execute(self) -> None:
        self.stopped = False
        while not self.stopped:
            self.execute_instruction()

    def stop(self) -> None:
        self.stopped = True

    def on_break_default(self, reason: int) -> None:
        self.stop()
        self.stop_reason = reason
        logger.warning(f"Execution stopped! Reason: {reason}")
