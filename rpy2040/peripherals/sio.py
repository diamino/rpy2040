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


def get_pinlist(mask: int) -> list[int]:
    return [i for i in range(32) if mask & (1 << i)]


class Sio(MemoryRegionMap):

    def __init__(self, base_address: int = SIO_START, size: int = SIO_SIZE):
        super().__init__("SIO", base_address, size)
        self.cpuid = 0  # Hardcoded '0' as we currently only support one core
        self.writehooks[SIO_GPIO_OUT_SET] = self.write_gpio_set
        self.writehooks[SIO_GPIO_OUT_CLR] = self.write_gpio_clr
        self.readhooks[SIO_CPUID] = self.read_cpuid

    def write_gpio_set(self, value: int) -> None:
        pinlist = get_pinlist(value)
        print(f">> GPIO pins set to HIGH/set: {pinlist}")

    def write_gpio_clr(self, value: int) -> None:
        pinlist = get_pinlist(value)
        print(f">> GPIO pins set to LOW/cleared: {pinlist}")

    def read_cpuid(self) -> int:
        return self.cpuid
