'''
SIO implementation of the RPy2040 project
'''
from .mpu import MemoryRegionMap

# SIO
SIO_START = 0xd0000000
SIO_SIZE = 0x1000000
# SIO registers
SIO_CPUID = 0x00
SIO_GPIO_OUT_SET = 0x14
SIO_GPIO_OUT_CLR = 0x18
SIO_DIV_UDIVIDEND = 0x60
SIO_DIV_UDIVISOR = 0x64
SIO_DIV_QUOTIENT = 0x70
SIO_DIV_REMAINDER = 0x74
SIO_DIV_CSR = 0x78


def get_pinlist(mask: int) -> list[int]:
    return [i for i in range(32) if mask & (1 << i)]


class Sio(MemoryRegionMap):

    def __init__(self, base_address: int = SIO_START, size: int = SIO_SIZE):
        super().__init__("SIO", base_address, size)
        self.cpuid = 0  # Hardcoded '0' as we currently only support one core
        self.div_csr = 1  # Reset value is 1 (ready)
        self.div_dividend = 0
        self.div_divisor = 0
        self.div_quotient = 0
        self.div_remainder = 0
        self.div_unsigned = True
        self.writehooks[SIO_GPIO_OUT_SET] = self.write_gpio_set
        self.writehooks[SIO_GPIO_OUT_CLR] = self.write_gpio_clr
        self.writehooks[SIO_DIV_UDIVIDEND] = self.write_div_udividend
        self.writehooks[SIO_DIV_UDIVISOR] = self.write_div_udivisor
        self.readhooks[SIO_CPUID] = self.read_cpuid
        self.readhooks[SIO_DIV_QUOTIENT] = self.read_div_quotient
        self.readhooks[SIO_DIV_REMAINDER] = self.read_div_remainder
        self.readhooks[SIO_DIV_CSR] = self.read_div_csr

    def write_gpio_set(self, value: int) -> None:
        pinlist = get_pinlist(value)
        print(f">> GPIO pins set to HIGH/set: {pinlist}")

    def write_gpio_clr(self, value: int) -> None:
        pinlist = get_pinlist(value)
        print(f">> GPIO pins set to LOW/cleared: {pinlist}")

    def read_cpuid(self) -> int:
        return self.cpuid

    def write_div_udividend(self, value: int) -> None:
        self.div_dividend = value
        self.div_unsigned = True
        self.do_division()

    def write_div_udivisor(self, value: int) -> None:
        self.div_divisor = value
        self.div_unsigned = True
        self.do_division()

    def read_div_quotient(self) -> int:
        return self.div_quotient

    def read_div_remainder(self) -> int:
        return self.div_remainder

    def read_div_csr(self) -> int:
        return self.div_csr

    def do_division(self):
        self.div_csr &= ~1
        if self.div_divisor != 0:
            self.div_quotient = self.div_dividend // self.div_divisor
            self.div_remainder = self.div_dividend % self.div_divisor
            self.div_csr |= 1
