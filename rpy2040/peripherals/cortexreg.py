'''
Cortex registers implementation of the RPy2040 project
'''
from .mpu import MemoryRegionMap

# Cortex register region
CORTEX_REGISTER_BASE = 0xe0000000
CORTEX_REGISTER_SIZE = 0xeda4
# Cortex registers
VTOR = 0xed08


class CortexRegisters(MemoryRegionMap):

    def __init__(self, base_address: int = CORTEX_REGISTER_BASE, size: int = CORTEX_REGISTER_SIZE):
        super().__init__("Cortex registers", base_address, size)
        self.vtor = 0
        self.writehooks[VTOR] = self.write_vtor
        self.readhooks[VTOR] = self.read_vtor

    def write_vtor(self, value: int) -> None:
        self.vtor = value

    def read_vtor(self) -> int:
        return self.vtor
