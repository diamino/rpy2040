'''
XOSC implementation of the RPy2040 project
'''
from .mpu import MemoryRegionMap

# XOSC
XOSC_BASE = 0x40024000
XOSC_SIZE = 0x20
# XOSC registers
XOSC_STATUS_OFFSET = 0x4
# XOSC masks
XOSC_STATUS_STABLE_BITS = 0x80000000


class Xosc(MemoryRegionMap):

    def __init__(self, base_address: int = XOSC_BASE, size: int = XOSC_SIZE):
        super().__init__("XOSC", base_address, size)
        self.readhooks[XOSC_STATUS_OFFSET] = self.read_status_offset

    def read_status_offset(self) -> int:
        return XOSC_STATUS_STABLE_BITS  # Hardcoded that the xosc is stable
