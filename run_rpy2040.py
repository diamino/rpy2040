import logging
from rpy2040.rpy2040 import Rp2040, loadbin

LOGGING_LEVEL = logging.ERROR

logger = logging.getLogger(__name__)


def main():  # pragma: no cover
    import argparse
    from functools import partial

    logging.basicConfig(level=LOGGING_LEVEL)

    parser = argparse.ArgumentParser(description='RPy2040 - a RP2040 emulator written in Python')

    base16 = partial(int, base=16)

    parser.add_argument('filename', type=str,
                        help='The binary (.bin) file to execute in the emulator')
    parser.add_argument('-e', '--entry_point', type=base16, nargs='?', const="0x10000000", default=None,
                        help='The entry point for execution in hex format (eg. 0x10000354). Defaults to 0x10000000 if no bootrom is loaded.')  # noqa: E501
    parser.add_argument('-b', '--bootrom', type=str,
                        help='The binary (.bin) file that holds the bootrom code. Defaults to bootrom.bin')
    parser.add_argument('-n', '--icount', type=int,
                        help='Limit the number of instructions to execute')
    parser.add_argument('-s', '--step', action='store_true',
                        help='Enable stepping per instruction')

    args = parser.parse_args()

    rp = Rp2040()
    loadbin(args.filename, rp.flash)

    if args.bootrom:
        loadbin(args.bootrom, rp.rom)
        rp.init_from_bootrom()

    if args.entry_point:
        rp.pc = args.entry_point

    if args.icount:
        for _ in range(args.icount):
            rp.execute_instruction()
            if args.step:
                input("* Press Enter to execute next instruction...")
    else:
        while True:
            rp.execute_instruction()
            if args.step:
                input("* Press Enter to execute next instruction...")


if __name__ == "__main__":  # pragma: no cover
    main()
