'''
RP2040 emulator written in Python

Inspired by the rp2040js emulator by Uri Shaked (https://github.com/wokwi/rp2040js)
'''
import array
import ctypes
from typing import Optional, Iterable, Protocol

IGNORE_BL = True

FLASH_START = 0x10000000
FLASH_SIZE = 16 * 1024 * 1024  # 16MB
SRAM_START = 0x20000000
SRAM_SIZE = 264 * 1024  # 264kB
SIO_START = 0xd0000000
SIO_SIZE = 0x1000000

UART0_BASE = 0x40034000
UART0_SIZE = 0x1000

SP_START = 0x20041000
PC_START = 0x10000000


class MemoryRegion(Protocol):

    base_address: int
    size: int

    def write_uint32(self, address: int, value: int) -> None:
        ...

    def read_uint32(self, address: int) -> int:
        ...


def loadbin(filename: str, mem: bytearray, offset: int = 0) -> None:
    with open(filename, 'rb') as fp:
        b = fp.read()
    mem[offset:len(b)+offset] = b


def sign_extend(value, no_bits_in: int, no_bits_out: int = 32) -> int:
    sign = (value >> (no_bits_in - 1)) & 1
    sign_bits = ~(~0 << (no_bits_out - no_bits_in))
    return ctypes.c_int32(((sign_bits if sign else 0) << no_bits_in) | value).value


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

    def write_uint32(self, address: int, value: int) -> None:
        region = self.find_region(address)
        if region:
            region.write_uint32(address - region.base_address, value)

    def read_uint32(self, address: int) -> int:
        region = self.find_region(address)
        if region:
            return region.read_uint32(address - region.base_address)
        return 0

    def read_uint16(self, address: int) -> int:
        region = self.find_region(address)
        if region:
            return region.read_uint16(address - region.base_address)
        return 0


class Uart(MemoryRegion):

    def __init__(self, base_address: int = UART0_BASE, size: int = UART0_SIZE):
        self.base_address = base_address
        self.size = size
        self.uartfr = 0

    def write_uint32(self, address: int, value: int) -> None:
        pass

    def read_uint32(self, address: int) -> int:
        if address == 0x18:  # UARTFR
            return self.uartfr
        else:
            raise MemoryError


class Sio(MemoryRegion):

    def __init__(self, base_address: int = SIO_START, size: int = SIO_SIZE):
        self.base_address = base_address
        self.size = size

    def write_uint32(self, address: int, value: int) -> None:
        if address == 20:  # GPIO SET
            pinlist = get_pinlist(value)
            print(f">> GPIO pins set to HIGH/set: {pinlist}")
        elif address == 24:  # GPIO CLR
            pinlist = get_pinlist(value)
            print(f">> GPIO pins set to LOW/cleared: {pinlist}")
        else:
            print(f">> Write of value [{value}/{value:#x}] to SIO address [{address + self.base_address:#010x}]")

    def read_uint32(self, address: int) -> int:
        print(f"<< Read from SIO address [{address + self.base_address:#010x}]")
        return 0

    def read_uint16(self, address: int) -> int:
        print(f"<< Read from SIO address [{address + self.base_address:#010x}]")
        return 0


class ByteArrayMemory(MemoryRegion):

    def __init__(self, base_address: int = SRAM_START, size: int = SRAM_SIZE, preinit: int = 0x00):
        self.base_address = base_address
        self.size = size
        self.memory = bytearray(size * [preinit])

    def write_uint32(self, address: int, value: int) -> None:
        self.memory[address:address+4] = value.to_bytes(4, byteorder='little')

    def read_uint32(self, address: int) -> int:
        return int.from_bytes(self.memory[address:address+4], 'little')

    def read_uint16(self, address: int) -> int:
        return int.from_bytes(self.memory[address:address+2], 'little')


class Rp2040:

    def __init__(self, pc: int = PC_START, sp: int = SP_START):
        self.registers = array.array('l', 16*[0])
        self.apsr: int = 0
        self.pc = pc
        self.sp = sp
        self.mmu = Mmu()
        self.sram_region = ByteArrayMemory(SRAM_START, SRAM_SIZE)
        self.flash_region = ByteArrayMemory(FLASH_START, FLASH_SIZE, 0xFF)
        self.sram = self.sram_region.memory
        self.flash = self.flash_region.memory
        self.mmu.register_region("flash", self.flash_region)
        self.mmu.register_region("sram", self.sram_region)
        self.mmu.register_region("sio", Sio())
        self.mmu.register_region("uart0", Uart())

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
        if (cond >> 1) == 0b000:  # EQ and NE
            result = self.apsr_z
        else:  # Eventually this clause should be deleted 
            result = True
        if (cond & 1) and cond != 0b1111:
            return not result
        else:
            return result

    def execute_intstruction(self) -> None:
        print(f"\nPC: {self.pc:x}\tSP: {self.sp:x}\tAPSR: {self.apsr:08x}")
        # instr_loc = self.pc - FLASH_START
        # opcode = int.from_bytes(self.flash[instr_loc:instr_loc+2], "little")
        opcode = self.mmu.read_uint16(self.pc)
        self.pc += 2
        opcode2 = 0
        if (opcode >> 11) == 0b11110:
            # instr_loc = self.pc - FLASH_START
            # opcode2 = int.from_bytes(self.flash[instr_loc:instr_loc+2], "little")
            opcode2 = self.mmu.read_uint16(self.pc)
            self.pc += 2

        print(self.str_registers(registers=range(4)))
        print(self.str_registers(registers=range(4, 8)))
        print(self.str_registers(registers=range(8, 12)))
        print(self.str_registers(registers=range(12, 16)))
        print(f"Current opcode is [{opcode:04x}]")
        # ADD (register) T2
        if (opcode >> 8) == 0b01000100:
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
        # BL
        elif (opcode >> 11) == 0b11110:
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
            imm32 = ctypes.c_int32((0b11111111 if s else 0) << 24 | imm23).value
            print(f"    {imm32=}")
            print(f"    Branch to: {(self.pc + imm32):#010x}")
            if not IGNORE_BL:
                self.lr = self.pc | 0x1
                self.pc += imm32
            else:
                print("    Branch ignored!!!")
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
        # LSLS (immediate)
        elif (opcode >> 11) == 0b00000:
            print("  LSLS (immediate) instruction...")
            m = (opcode >> 3) & 0x07
            d = opcode & 0x07
            shift_n = (opcode >> 6) & 0x1F
            print(f"    Source R[{m}]\tDestination R[{d}]\tShift amount [{shift_n}]")
            self.registers[d] = (self.registers[m] << shift_n) & 0xFFFFFFFF
            # TODO: update flags
        # LSLS (register)
        elif (opcode >> 6) == 0b0100000010:
            print("  LSLS (register) instruction...")
            m = (opcode >> 3) & 0x7
            d = opcode & 0x7
            shift_n = self.registers[m] & 0xFF
            print(f"    Source and destination R[{d}]\tShift amount [{shift_n}]")
            self.registers[d] = (self.registers[d] << shift_n) & 0xFFFFFFFF
            # TODO: update flags
        # MOVS
        elif (opcode >> 11) == 0b00100:
            print("  MOVS instruction...")
            d = (opcode >> 8) & 0x07
            value = opcode & 0xFF
            print(f"    Destination register is [{d}]\tValue is [{value}]")
            self.registers[d] = value
            # TODO: update flags
        # MOV (register)
        elif (opcode >> 8) == 0b01000110:
            print("  MOV (register) instruction...")
            d = ((opcode >> 4) & 0x08) | (opcode & 0x7)
            m = (opcode >> 3) & 0xF
            print(f"    Source R[{m}]\tDestination R[{d}]")
            self.registers[d] = self.registers[m]
            # TODO: update flags
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
        # STR immediate (T1)
        elif (opcode >> 11) == 0b01100:
            print("  STR (immediate) instruction...")
            n = (opcode >> 3) & 0x7
            t = opcode & 0x7
            imm = ((opcode >> 6) & 0x1F) << 2
            address = self.registers[n] + imm
            print(f"    Source R[{t}]\tDestination address [{address:#010x}]")
            self.mmu.write_uint32(address, self.registers[t])
        # TST immediate (T1)
        elif (opcode >> 6) == 0b0100001000:
            print("  TST instruction...")
            n = opcode & 0x7
            m = (opcode >> 3) & 0x7
            result = self.registers[n] & self.registers[m]
            self.apsr_n = bool(result & (1 << 31))
            self.apsr_z = bool(result == 0)
            print(f"  APSR: {self.apsr:08x}")
        else:
            print(" Instruction not implemented!!!!")
            raise NotImplementedError


def main():  # pragma: no cover
    import argparse
    from functools import partial

    parser = argparse.ArgumentParser(description='RPy2040 - a RP2040 emulator written in Python')

    base16 = partial(int, base=16)

    parser.add_argument('filename', type=str,
                        help='The binary file to execute in the emulator')
    parser.add_argument('entry_point', type=base16, nargs='?', default="0x10000000",
                        help='The entry point for execution in hex format (eg. 0x10000354)')

    args = parser.parse_args()

    rp = Rp2040(pc=args.entry_point)
    loadbin(args.filename, rp.flash)
    for _ in range(30):
        rp.execute_intstruction()


if __name__ == "__main__":  # pragma: no cover
    main()
