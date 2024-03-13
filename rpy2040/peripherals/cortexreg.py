'''
Cortex registers implementation of the RPy2040 project
'''
from functools import partial
from .mpu import MemoryRegionMap, ReadHookType, WriteHookType

# Cortex register region
CORTEX_REGISTER_BASE = 0xe0000000
CORTEX_REGISTER_SIZE = 0xeda4
# Cortex registers
NVIC_ISER = 0xe100
NVIC_ICER = 0xe180
NVIC_ISPR = 0xe200
NVIC_ICPR = 0xe280
NVIC_IPR_BASE = 0xe400
VTOR = 0xed08


class CortexRegisters(MemoryRegionMap):

    def __init__(self, base_address: int = CORTEX_REGISTER_BASE, size: int = CORTEX_REGISTER_SIZE):
        super().__init__("Cortex registers", base_address, size)
        self.pending_interrupts = 0
        self.enabled_interrupts = 0
        self.interrupt_levels = [0xffffffff, 0, 0, 0]
        self.vtor = 0
        self.writehooks[NVIC_ISER] = self.write_nvic_iser
        self.writehooks[NVIC_ICER] = self.write_nvic_icer
        self.writehooks[NVIC_ISPR] = self.write_nvic_ispr
        self.writehooks[NVIC_ICPR] = self.write_nvic_icpr
        self.readhooks[NVIC_ISER] = self.read_nvic_iser
        self.readhooks[NVIC_ICER] = self.read_nvic_icer
        self.readhooks[NVIC_ISPR] = self.read_nvic_ispr
        self.readhooks[NVIC_ICPR] = self.read_nvic_icpr
        for ipr_nr in range(8):
            self.writehooks[NVIC_IPR_BASE + (ipr_nr * 4)] = self.write_nvic_ipr(ipr_nr)
            self.readhooks[NVIC_IPR_BASE + (ipr_nr * 4)] = self.read_nvic_ipr(ipr_nr)
        self.writehooks[VTOR] = self.write_vtor
        self.readhooks[VTOR] = self.read_vtor

    def write_nvic_iser(self, value: int) -> None:
        self.enabled_interrupts |= value

    def read_nvic_iser(self) -> int:
        return self.enabled_interrupts

    def write_nvic_icer(self, value: int) -> None:
        self.enabled_interrupts &= ~value

    def read_nvic_icer(self) -> int:
        return self.enabled_interrupts

    def write_nvic_ispr(self, value: int) -> None:
        self.pending_interrupts |= value

    def read_nvic_ispr(self) -> int:
        return self.pending_interrupts

    def write_nvic_icpr(self, value: int) -> None:
        self.pending_interrupts &= ~value

    def read_nvic_icpr(self) -> int:
        return self.pending_interrupts

    def write_nvic_ipr(self, ipr_nr: int) -> WriteHookType:
        return partial(self.write_nvic_ipr_partial, ipr_nr=ipr_nr)

    def write_nvic_ipr_partial(self, value: int, ipr_nr: int) -> None:
        for i in range(4):
            interrupt_nr = (ipr_nr * 4) + i
            priority = (value >> ((i * 8) + 6)) & 0x3
            for level in range(4):
                self.interrupt_levels[level] &= ~(1 << interrupt_nr)
            self.interrupt_levels[priority] |= (1 << interrupt_nr)

    def read_nvic_ipr(self, ipr_nr: int) -> ReadHookType:
        return partial(self.read_nvic_ipr_partial, ipr_nr=ipr_nr)

    def read_nvic_ipr_partial(self, ipr_nr: int) -> int:
        regvalue = 0
        for level in range(4):
            for i in range(4):
                if self.interrupt_levels[level] & (1 << ((ipr_nr * 4) + i)):
                    regvalue |= level << ((i * 8) + 6)
        return regvalue

    def write_vtor(self, value: int) -> None:
        self.vtor = value

    def read_vtor(self) -> int:
        return self.vtor
