'''
Resets register implementation of the RPy2040 project
'''
from .mpu import MemoryRegionMap

# Resets
RESETS_BASE = 0x4000c000
RESETS_SIZE = 0xc
# Resets registers
RESETS_RESET_DONE = 0x8
# Resets masks
RESETS_RESET_BITS = 0x01ffffff


class Resets(MemoryRegionMap):

    def __init__(self, base_address: int = RESETS_BASE, size: int = RESETS_SIZE):
        super().__init__("Resets", base_address, size)
        self.readhooks[RESETS_RESET_DONE] = self.read_reset_done

    def read_reset_done(self) -> int:
        return RESETS_RESET_BITS
