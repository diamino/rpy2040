'''
UART implementation of the RPy2040 project
'''
from .mpu import MemoryRegionMap

# UART
UART0_BASE = 0x40034000
UART0_SIZE = 0x1000
# UART registers
UARTDR = 0x00
UARTFR = 0x18
UARTIBRD = 0x24
UARTFBRD = 0x28
UARTCR = 0x30


class Uart(MemoryRegionMap):

    def __init__(self, base_address: int = UART0_BASE, size: int = UART0_SIZE):
        super().__init__("UART", base_address, size)
        self.uartfr = 0
        self.uartcr = 1
        self.writehooks[UARTDR] = self.write_uartdr
        self.readhooks[UARTFR] = self.read_uartfr
        self.readhooks[UARTIBRD] = self.read_uartibrd
        self.readhooks[UARTFBRD] = self.read_uartfbrd
        self.readhooks[UARTCR] = self.read_uartcr

    def write_uartdr(self, value: int) -> None:
        print(f"UART: Write to data register [{value:#x}/'{chr(value)}']...")

    def read_uartfr(self) -> int:
        return self.uartfr

    def read_uartibrd(self) -> int:
        return 0

    def read_uartfbrd(self) -> int:
        return 0

    def read_uartcr(self) -> int:
        return self.uartcr
