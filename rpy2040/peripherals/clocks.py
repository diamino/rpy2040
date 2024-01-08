'''
Clocks implementation of the RPy2040 project
'''
from .mpu import MemoryRegionMap

# Clocks
CLOCKS_BASE = 0x40008000
CLOCKS_SIZE = 0xc8
# Clocks registers
CLK_REF_SELECTED = 0x38
CLK_SYS_SELECTED = 0x44
# Clocks masks


class Clocks(MemoryRegionMap):

    def __init__(self, base_address: int = CLOCKS_BASE, size: int = CLOCKS_SIZE):
        super().__init__("Clocks", base_address, size)
        self.readhooks[CLK_REF_SELECTED] = self.read_ref_selected
        self.readhooks[CLK_SYS_SELECTED] = self.read_sys_selected

    def read_ref_selected(self) -> int:
        return 1

    def read_sys_selected(self) -> int:
        return 1
