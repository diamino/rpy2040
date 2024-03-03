import struct
import logging

logger = logging.getLogger("uf2")

UF2_FILE = './examples/binaries/uart/hello_uart/hello_uart.uf2'
MAGICSTART0 = 0x0A324655
MAGICSTART1 = 0x9E5D5157
MAGICEND = 0x0AB16F30

NOT_MAIN_FLASH = 0x00000001
FILE_CONTAINER = 0x00001000
FAMILYID_PRESENT = 0x00002000
MD5_CHECKSUM_PRESENT = 0x00004000
EXTENSION_TAGS_PRESENT = 0x00008000


def loaduf2(filename: str, mem: bytearray, offset: int = 0) -> None:
    with open(filename, 'rb') as fp:
        while True:
            # Read 512-byte block
            block = fp.read(512)
            if len(block) == 0:
                logger.debug("End of file reached...")
                break
            if len(block) < 512:
                logger.warning("Block is not 512-bytes!")
                break
            (magicstart0, magicstart1, flags, targetaddr,
                payloadsize, blockno, numblocks, filesize) = struct.unpack("<"+"I"*8, block[0:32])
            magicend = int.from_bytes(block[-4:], 'little')
            if magicstart0 != MAGICSTART0 or magicstart1 != MAGICSTART1 or magicend != MAGICEND:
                logger.error("Block starts or ends with wrong magic value! Misaligned? Skipping...")
                continue
            if flags & NOT_MAIN_FLASH:
                logger.debug("Non main flash block. Skipping...")
                continue
            if payloadsize > 476:
                logger.warning("It seems that the payloadSize is to big. Skipping...")
                continue
            addr = targetaddr - offset
            mem[addr:addr + payloadsize] = block[32:32 + payloadsize]
            logger.debug(f"{flags=:x}\t{targetaddr=:x}\t{payloadsize=}\t{blockno=}\t{numblocks=}\t{filesize=:x}")


if __name__ == "__main__":
    mem = bytearray(0x2400)
    loaduf2(UF2_FILE, mem, offset=0x10000000)
    print(f"{mem}")
