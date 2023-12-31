'''
MPU implementation of the RPy2040 project
'''
from typing import Protocol, Optional, Callable


class MemoryRegion(Protocol):

    base_address: int
    size: int

    def write(self, address: int, value: int, num_bytes: int = 4) -> None:
        ...

    def read(self, address: int, num_bytes: int = 4) -> int:
        ...


def generate_mask(region: MemoryRegion) -> Optional[int]:
    if region.size.bit_count() != 1:
        return None
    mask = ~(region.size - 1)
    if region.base_address == region.base_address & mask:
        return mask
    else:
        return None


ReadHookType = Callable[[], int]
WriteHookType = Callable[[int], None]


class MemoryRegionMap:

    def __init__(self, name: str, base_address: int, size: int):
        self.base_address = base_address
        self.size = size
        self.name = name
        self.writehooks: dict[int, WriteHookType] = {}
        self.readhooks: dict[int, ReadHookType] = {}

    def write(self, address: int, value: int, num_bytes: int = 4) -> None:
        if address in self.writehooks:
            self.writehooks[address](value)
        else:
            print(f">> Write of value [{value}/{value:#x}] to {self.name} address [{address + self.base_address:#010x}]")  # noqa: E501
            # raise MemoryError

    def read(self, address: int, num_bytes: int = 4) -> int:
        if address in self.readhooks:
            return self.readhooks[address]()
        else:
            print(f"<< Read {num_bytes} bytes from {self.name} address [{address + self.base_address:#010x}]")
            # return 0
            raise MemoryError


class Mpu:

    def __init__(self):
        self.regions = {}
        self.masks = {}

    def register_region(self, name: str, region: MemoryRegion) -> None:
        self.regions[name] = region
        self.masks[name] = generate_mask(region)

    def find_region(self, address: int) -> Optional[MemoryRegion]:
        for _, region in self.regions.items():
            if (address >= region.base_address) and (address < (region.base_address + region.size)):
                return region
        print(f"MMU: No matching region found for address {address:#010x}!!!")
        return None

    def write(self, address: int, value: int, num_bytes: int = 4) -> None:
        region = self.find_region(address)
        if region:
            region.write(address - region.base_address, value, num_bytes)

    def read(self, address: int, num_bytes: int = 4) -> int:
        region = self.find_region(address)
        if region:
            return region.read(address - region.base_address, num_bytes)
        return 0

    def write_uint32(self, address: int, value: int) -> None:
        self.write(address, value, 4)

    def read_uint32(self, address: int) -> int:
        return self.read(address, 4)

    def read_uint16(self, address: int) -> int:
        return self.read(address, 2)

    def read_uint8(self, address: int) -> int:
        return self.read(address, 1)
