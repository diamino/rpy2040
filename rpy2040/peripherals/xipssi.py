'''
XIP SSI implementation of the RPy2040 project
'''
from .mpu import MemoryRegionMap

# XIP SSI
XIP_SSI_BASE = 0x18000000
XIP_SSI_SIZE = 0x100
# XIP SSI registers
SSI_SR_OFFSET = 0x28
SSI_DR0_OFFSET = 0x60
# XIP SSI masks
SSI_SR_TFE_BITS = 0x00000004
SSI_SR_BUSY_BITS = 0x00000001


class XipSsi(MemoryRegionMap):

    def __init__(self, base_address: int = XIP_SSI_BASE, size: int = XIP_SSI_SIZE):
        super().__init__("XIP SSI", base_address, size)
        self.dr0 = 0
        self.writehooks[SSI_DR0_OFFSET] = self.write_dr0_offset
        self.readhooks[SSI_DR0_OFFSET] = self.read_dr0_offset
        self.readhooks[SSI_SR_OFFSET] = self.read_sr_offset

    def write_dr0_offset(self, value: int) -> None:
        if value == 0x05:  # CMD_READ_STATUS
            self.dr0 = 0

    def read_sr_offset(self) -> int:
        return SSI_SR_TFE_BITS  # Hardcoded that the transmit buffer is empty

    def read_dr0_offset(self) -> int:
        return self.dr0
