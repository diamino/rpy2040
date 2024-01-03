'''
Memory block implementation of the RPy2040 project
'''


class ByteArrayMemory:

    def __init__(self, base_address: int, size: int, preinit: int = 0x00):
        self.base_address = base_address
        self.size = size
        self.memory = bytearray(size * [preinit])

    def write(self, address: int, value: int, num_bytes: int = 4) -> None:
        self.memory[address:address+num_bytes] = value.to_bytes(num_bytes, byteorder='little')

    def read(self, address: int, num_bytes: int = 4) -> int:
        return int.from_bytes(self.memory[address:address+num_bytes], 'little')
