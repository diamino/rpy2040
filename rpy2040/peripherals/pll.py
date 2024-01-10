'''
PLL implementation of the RPy2040 project
'''
from .mpu import MemoryRegionMap

# PLL
PLL_SYS_BASE = 0x40028000
PLL_USB_BASE = 0x4002c000
PLL_SIZE = 0x10
# PLL registers
PLL_CS_OFFSET = 0x0
PLL_FBDIV_INT_OFFSET = 0x8
PLL_PRIM_OFFSET = 0xc
# PLL masks
PLL_CS_LOCK_BITS = 0x80000000


class Pll(MemoryRegionMap):

    def __init__(self, base_address: int = PLL_SYS_BASE, size: int = PLL_SIZE):
        super().__init__("PLL", base_address, size)
        self.readhooks[PLL_CS_OFFSET] = self.read_cs
        self.readhooks[PLL_FBDIV_INT_OFFSET] = self.read_fbdiv_int
        self.readhooks[PLL_PRIM_OFFSET] = self.read_prim

    def read_cs(self) -> int:
        return PLL_CS_LOCK_BITS | 1  # Hardcoded that the PLL is locked and REFDIV = 1

    def read_fbdiv_int(self) -> int:
        return 0x7d

    def read_prim(self) -> int:
        return (6 << 16) | (2 << 12)
