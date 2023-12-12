'''
RP2040 emulator written in Python

Inspired by the rp2040js emulator by Uri Shaked (https://github.com/wokwi/rp2040js)
'''
import array
import ctypes

FLASH_START = 0x10000000
FLASH_SIZE = 16 * 1024 * 1024  # 16MB
SRAM_START = 0x20000000
SRAM_SIZE = 264 * 1024  # 264kB
SIO_START = 0xd0000000
SIO_SIZE = 0x1000000

SP_START = 0x20041000
PC_START = 0x10000000


def loadbin(filename: str, mem: bytearray, offset: int = 0):
    with open(filename, 'rb') as fp:
        b = fp.read()
    mem[offset:len(b)+offset] = b


def align(x, y):
    return y * (x // y)  


class Rp2040:

    def __init__(self, pc: int = PC_START, sp: int = SP_START):
        self.sram = bytearray(SRAM_SIZE)
        self.flash = bytearray(FLASH_SIZE * [0xff])  # initialized with FF
        self.registers = array.array('l', 16*[0])
        self.pc = pc
        self.sp = sp

    @property
    def pc(self):
        return self.registers[15]

    @pc.setter
    def pc(self, value: int):
        self.registers[15] = value

    @property
    def sp(self):
        return self.registers[13]

    @sp.setter
    def sp(self, value: int):
        self.registers[13] = value

    @property
    def lr(self):
        return self.registers[14]

    @lr.setter
    def lr(self, value: int):
        self.registers[14] = value

    def write_uint32(self, address: int, value: int):
        if (address >= SRAM_START) and (address < (SRAM_START + SRAM_SIZE)):
            sram_offset = address - SRAM_START
            self.sram[sram_offset:sram_offset+4] = value.to_bytes(4, byteorder='little')
        elif (address >= SIO_START) and (address < (SIO_START + SIO_SIZE)):
            print(f"Write of value [{value}/{value:#x}] to address [{address:#08x}]")

    def read_uint32(self, address: int):
        if (address >= SRAM_START) and (address < (SRAM_START + SRAM_SIZE)):
            # read from SRAM
            sram_offset = address - SRAM_START
            return int.from_bytes(self.sram[sram_offset:sram_offset+4], 'little')
        elif (address >= FLASH_START) and (address < (FLASH_START + FLASH_SIZE)):
            # read from flash
            flash_offset = address - FLASH_START
            return int.from_bytes(self.flash[flash_offset:flash_offset+4], 'little')
        elif (address >= SIO_START) and (address < (SIO_START + SIO_SIZE)):
            print(f"Read from SIO address [{address:#08x}]")

    def read_uint16(self, address: int):
        if (address >= SRAM_START) and (address < (SRAM_START + SRAM_SIZE)):
            # read from SRAM
            sram_offset = address - SRAM_START
            return int.from_bytes(self.sram[sram_offset:sram_offset+2], 'little')
        elif (address >= FLASH_START) and (address < (FLASH_START + FLASH_SIZE)):
            # read from flash
            flash_offset = address - FLASH_START
            return int.from_bytes(self.flash[flash_offset:flash_offset+2], 'little')
        elif (address >= SIO_START) and (address < (SIO_START + SIO_SIZE)):
            print(f"Read from SIO address [{address:#08x}]")

    def execute_intstruction(self):
        print(f"\nPC: {self.pc:x}\tSP: {self.sp:x}")
        # instr_loc = self.pc - FLASH_START
        # opcode = int.from_bytes(self.flash[instr_loc:instr_loc+2], "little")
        opcode = self.read_uint16(self.pc)
        self.pc += 2
        if (opcode >> 11) == 0b11110:
            # instr_loc = self.pc - FLASH_START
            # opcode2 = int.from_bytes(self.flash[instr_loc:instr_loc+2], "little")
            opcode2 = self.read_uint16(self.pc)
            self.pc += 2

        print(f"Registers: {self.registers}")
        print(f"Current opcode is [{opcode:04x}]")
        # BL
        if (opcode >> 11) == 0b11110:
            print("  BL instruction...")
            imm10 = opcode & 0x3ff 
            imm11 = opcode2 & 0x7ff
            j1 = bool(opcode2 & 0x2000)
            j2 = bool(opcode2 & 0x800)
            s = bool(opcode & 0x400)
            i1 = not (j1 ^ s)
            i2 = not (j2 ^ s)
            print(f"  {j1=} {j2=} {s=} {i1=} {i2=} {imm10=} {imm11=}")
            imm32 = ctypes.c_int32((0b11111111 if s else 0) << 24 | int(i1) << 23 | int(i2) << 22 | imm10 << 12 | imm11 << 1).value
            print(f"  {imm32=}")
            self.lr = self.pc | 0x1
            self.pc += imm32
        # LDR (immediate)
        elif (opcode >> 11) == 0b01101:
            print("  LDR (immediate) instruction...")
            n = (opcode >> 3) & 0x7
            t = opcode & 0x7
            imm = ((opcode >> 6) & 0x1F) << 2
            address = self.registers[n] + imm
            print(f"  Destination R[{t}]\tSource address [{address:#08x}]")
            self.registers[t] = self.read_uint32(address)
        # LDR (literal)
        elif (opcode >> 11) == 0b01001:
            print("  LDR (literal) instruction...")
            t = (opcode >> 8) & 0x7
            imm = (opcode & 0xFF) << 2
            base = (self.pc + 2) & 0xfffffffc
            address = base + imm
            print(f"  Destination R[{t}]\tSource address [{address:#08x}]")
            self.registers[t] = self.read_uint32(address)
        # LSLS (immediate)
        elif (opcode >> 11) == 0b00000:
            print("  LSLS (immediate) instruction...")
            m = (opcode >> 3) & 0x07
            d = opcode & 0x07
            shift_n = (opcode >> 6) & 0x1F
            print(f"  Source R[{m}]\tDestination R[{d}]\tShift amount [{shift_n}]")
            self.registers[d] = (self.registers[m] << shift_n) & 0xFFFFFFFF
            # TODO: update flags
        # LSLS (register)
        elif (opcode >> 6) == 0b0100000010:
            print("  LSLS (regsiter) instruction...")
            m = (opcode >> 3) & 0x7
            d = opcode & 0x7
            shift_n = self.registers[m] & 0xFF
            print(f"  Source and destination R[{d}]\tShift amount [{shift_n}]")
            self.registers[d] = (self.registers[d] << shift_n) & 0xFFFFFFFF
            # TODO: update flags
        # MOVS
        elif (opcode >> 11) == 0b00100:
            print("  MOVS instruction...")
            d = (opcode >> 8) & 0x07
            value = opcode & 0xFF
            print(f"  Destination registers is [{d}]\tValue is [{value}]")
            self.registers[d] = value
            # TODO: update flags
        # PUSH
        elif (opcode >> 9) == 0b1011010:
            print("  PUSH instruction...")
            bitcount = (opcode & 0x1FF).bit_count()
            address = self.sp - 4 * bitcount
            for i in range(8):
                if (opcode & (1 << i)):
                    self.write_uint32(address, self.registers[i])
                    address += 4
            if (opcode & (1 << 8)):  # 'M'-bit -> push LR register 
                self.write_uint32(address, self.registers[14])
            self.sp -= 4 * bitcount
        # STR immediate (T1)
        elif (opcode >> 11) == 0b01100:
            print("  STR (immediate) instruction...")
            n = (opcode >> 3) & 0x7
            t = opcode & 0x7
            imm = ((opcode >> 6) & 0x1F) << 2
            address = self.registers[n] + imm
            print(f"  Source R[{t}]\tDestination address [{address:#08x}]")
            self.write_uint32(address, self.registers[t])
        else:
            print(" Instruction not implemented!!!!")


def main():
    rp = Rp2040(pc=0x10000354)
    loadbin("./binaries/blink/blink.bin", rp.flash)
    for _ in range(20):
        rp.execute_intstruction()


if __name__ == "__main__":
    main()
