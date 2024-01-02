'''
RP2040 emulator written in Python

Inspired by the rp2040js emulator by Uri Shaked (https://github.com/wokwi/rp2040js)
'''
import array
import ctypes
from typing import Optional, Iterable, Protocol

DEBUG_REGISTERS = True
DEBUG_INSTRUCTIONS = False

IGNORE_BL = False

ROM_START = 0x00000000
ROM_SIZE = 16 * 1024  # 16kB
FLASH_START = 0x10000000
FLASH_SIZE = 16 * 1024 * 1024  # 16MB
SRAM_START = 0x20000000
SRAM_SIZE = 264 * 1024  # 264kB
SIO_START = 0xd0000000
SIO_SIZE = 0x1000000

UART0_BASE = 0x40034000
UART0_SIZE = 0x1000
UARTDR = 0x00
UARTFR = 0x18

CORTEX_REGISTER_BASE = 0xe0000000
CORTEX_REGISTER_SIZE = 0xeda4
VTOR = 0xed08

SP_START = 0x20041000
PC_START = 0x10000000


class MemoryRegion(Protocol):

    base_address: int
    size: int

    def write(self, address: int, value: int, num_bytes: int = 4) -> None:
        ...

    def read(self, address: int, num_bytes: int = 4) -> int:
        ...


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


def get_pinlist(mask: int) -> list[int]:
    return [i for i in range(32) if mask & (1 << i)]


def generate_mask(region: MemoryRegion) -> Optional[int]:
    if region.size.bit_count() != 1:
        return None
    mask = ~(region.size - 1)
    if region.base_address == region.base_address & mask:
        return mask
    else:
        return None


class Mmu:

    def __init__(self):
        self.regions = {}
        self.masks = {}

    def register_region(self, name: str, region: MemoryRegion) -> None:
        self.regions[name] = region
        self.masks[name] = generate_mask(region)

    def find_region(self, address: int) -> Optional[MemoryRegion]:
        for _, region in self.regions.items():
            if (address >= region.base_address) and (address < (region.base_address + region.size)):
                return region
        print(f"MMU: No matching region found for address {address:#010x}!!!")
        return None

    def write(self, address: int, value: int, num_bytes: int = 4) -> None:
        region = self.find_region(address)
        if region:
            region.write(address - region.base_address, value, num_bytes)

    def read(self, address: int, num_bytes: int = 4) -> int:
        region = self.find_region(address)
        if region:
            return region.read(address - region.base_address, num_bytes)
        return 0

    def write_uint32(self, address: int, value: int) -> None:
        self.write(address, value, 4)

    def read_uint32(self, address: int) -> int:
        return self.read(address, 4)

    def read_uint16(self, address: int) -> int:
        return self.read(address, 2)

    def read_uint8(self, address: int) -> int:
        return self.read(address, 1)


class Uart(MemoryRegion):

    def __init__(self, base_address: int = UART0_BASE, size: int = UART0_SIZE):
        self.base_address = base_address
        self.size = size
        self.uartfr = 0

    def write(self, address: int, value: int, num_bytes: int = 4) -> None:
        if address == UARTDR:
            print(f"UART: Write to data register [{value:#x}/'{chr(value)}']...")
        else:
            print(f"UART: Write of value {value:#x} to UART address {address:#x}...")

    def read(self, address: int, num_bytes: int = 4) -> int:
        if address == UARTFR:
            return self.uartfr
        else:
            raise MemoryError


class Sio(MemoryRegion):

    def __init__(self, base_address: int = SIO_START, size: int = SIO_SIZE):
        self.base_address = base_address
        self.size = size

    def write(self, address: int, value: int, num_bytes: int = 4) -> None:
        if address == 20:  # GPIO SET
            pinlist = get_pinlist(value)
            print(f">> GPIO pins set to HIGH/set: {pinlist}")
        elif address == 24:  # GPIO CLR
            pinlist = get_pinlist(value)
            print(f">> GPIO pins set to LOW/cleared: {pinlist}")
        else:
            print(f">> Write of value [{value}/{value:#x}] to SIO address [{address + self.base_address:#010x}]")

    def read(self, address: int, num_bytes: int = 4) -> int:
        print(f"<< Read {num_bytes} bytes from SIO address [{address + self.base_address:#010x}]")
        return 0


class ByteArrayMemory(MemoryRegion):

    def __init__(self, base_address: int = SRAM_START, size: int = SRAM_SIZE, preinit: int = 0x00):
        self.base_address = base_address
        self.size = size
        self.memory = bytearray(size * [preinit])

    def write(self, address: int, value: int, num_bytes: int = 4) -> None:
        self.memory[address:address+num_bytes] = value.to_bytes(num_bytes, byteorder='little')

    def read(self, address: int, num_bytes: int = 4) -> int:
        return int.from_bytes(self.memory[address:address+num_bytes], 'little')


class CortexRegisters(MemoryRegion):

    def __init__(self, base_address: int = CORTEX_REGISTER_BASE, size: int = CORTEX_REGISTER_SIZE):
        self.base_address = base_address
        self.size = size

    def write(self, address: int, value: int, num_bytes: int = 4) -> None:
        pass

    def read(self, address: int, num_bytes: int = 4) -> int:
        if address == VTOR:
            return 0
        print(f"Read from unimplemented Cortex register [{address:#x}]!!!")
        return 0


class Rp2040:

    def __init__(self):
        self.registers = array.array('l', 16*[0])
        self.apsr: int = 0
        self.pc = PC_START
        self.sp = SP_START
        self.mmu = Mmu()
        self.rom_region = ByteArrayMemory(ROM_START, ROM_SIZE)
        self.sram_region = ByteArrayMemory(SRAM_START, SRAM_SIZE)
        self.flash_region = ByteArrayMemory(FLASH_START, FLASH_SIZE, 0xFF)
        self.cortex_region = CortexRegisters(CORTEX_REGISTER_BASE, CORTEX_REGISTER_SIZE)
        self.rom = self.rom_region.memory
        self.sram = self.sram_region.memory
        self.flash = self.flash_region.memory
        self.mmu.register_region("flash", self.flash_region)
        self.mmu.register_region("sram", self.sram_region)
        self.mmu.register_region("rom", self.rom_region)
        self.mmu.register_region("cortex0", self.cortex_region)
        self.mmu.register_region("sio", Sio())
        self.mmu.register_region("uart0", Uart())

    def init_from_bootrom(self):
        self.sp = self.rom_region.read(0)
        self.pc = self.rom_region.read(4) & 0xfffffffe

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
        opcode = self.mmu.read_uint16(self.pc)
        self.pc += 2
        opcode2 = 0
        if (opcode >> 11) == 0b11110:
            # instr_loc = self.pc - FLASH_START
            # opcode2 = int.from_bytes(self.flash[instr_loc:instr_loc+2], "little")
            opcode2 = self.mmu.read_uint16(self.pc)
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
            if not IGNORE_BL:
                self.lr = self.pc | 0x1
                self.pc += imm32
            else:
                print("    Branch ignored!!!")
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
                    self.registers[i] = self.mmu.read_uint32(address)
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
            self.registers[t] = self.mmu.read_uint32(address)
        # LDR (literal)
        elif (opcode >> 11) == 0b01001:
            print("  LDR (literal) instruction...")
            t = (opcode >> 8) & 0x7
            imm = (opcode & 0xFF) << 2
            base = (self.pc + 2) & 0xfffffffc
            address = base + imm
            print(f"    Destination R[{t}]\tSource address [{address:#010x}]")
            self.registers[t] = self.mmu.read_uint32(address)
        # LDRB (immediate)
        elif (opcode >> 11) == 0b01111:
            print("  LDRB (immediate) instruction...")
            imm5 = (opcode >> 6) & 0x1F
            n = (opcode >> 3) & 0x7
            t = opcode & 0x7
            address = self.registers[n] + imm5
            print(f"    Destination R[{t}]\tSource address [{address:#010x}]")
            self.registers[t] = self.mmu.read_uint8(address)
        # LDRSH (register)
        elif (opcode >> 9) == 0b0101111:
            print("  LDRSH (register) instruction...")
            m = (opcode >> 6) & 0x7
            n = (opcode >> 3) & 0x7
            t = opcode & 0x7
            address = self.registers[n] + self.registers[m]
            print(f"    Destination R[{t}]\tSource address [{address:#010x}]")
            self.registers[t] = self.mmu.read_uint16(address)
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
        # MOVS
        elif (opcode >> 11) == 0b00100:
            print("  MOVS instruction...")
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
        # PUSH
        elif (opcode >> 9) == 0b1011010:
            print("  PUSH instruction...")
            bitcount = (opcode & 0x1FF).bit_count()
            address = self.sp - 4 * bitcount
            for i in range(8):
                if (opcode & (1 << i)):
                    self.mmu.write_uint32(address, self.registers[i])
                    address += 4
            if (opcode & (1 << 8)):  # 'M'-bit -> push LR register
                self.mmu.write_uint32(address, self.registers[14])
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
        # STR immediate (T1)
        elif (opcode >> 11) == 0b01100:
            print("  STR (immediate) instruction...")
            n = (opcode >> 3) & 0x7
            t = opcode & 0x7
            imm = ((opcode >> 6) & 0x1F) << 2
            address = self.registers[n] + imm
            print(f"    Source R[{t}]\tDestination address [{address:#010x}]")
            self.mmu.write_uint32(address, self.registers[t])
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


def main():  # pragma: no cover
    import argparse
    from functools import partial

    parser = argparse.ArgumentParser(description='RPy2040 - a RP2040 emulator written in Python')

    base16 = partial(int, base=16)

    parser.add_argument('filename', type=str,
                        help='The binary (.bin) file to execute in the emulator')
    parser.add_argument('-e', '--entry_point', type=base16, nargs='?', const="0x10000000", default=None,
                        help='The entry point for execution in hex format (eg. 0x10000354). Defaults to 0x10000000 if no bootrom is loaded.')  # noqa: E501
    parser.add_argument('-b', '--bootrom', type=str,
                        help='The binary (.bin) file that holds the bootrom code. Defaults to bootrom.bin')

    args = parser.parse_args()

    rp = Rp2040()
    loadbin(args.filename, rp.flash)

    if args.bootrom:
        loadbin(args.bootrom, rp.rom)
        rp.init_from_bootrom()

    if args.entry_point:
        rp.pc = args.entry_point

    for _ in range(10):
        rp.execute_instruction()


if __name__ == "__main__":  # pragma: no cover
    main()
