# RPy2040

RP2040 chip emulator written in Python

The code is loosely based on the [rp2040js code](https://github.com/wokwi/rp2040js) from the [excellent live coding series](https://youtube.com/playlist?list=PLLomdjsHtJTxT-vdJHwa3z62dFXZnzYBm&si=1AcioLyIXY0Y92L1) by Uri Shaked of [Wokwi](https://wokwi.com).

The tags in the repository (loosely) refer to the resulting code after each episode of the live coding series.

## Requirements

* Python 3 (tested on v3.11.3)
* Pytest to run the tests

You have to supply your own compiled binaries (for RP2040) to be executed.

## Usage

In the repo are two scripts to use the RP2040 emulator. One simple script to run a binary executable (`run_rpy2040.py`) and one with an integrated GDB server (`gdbserver.py`).

Default run script:
```bash
usage: run_rpy2040.py [-h] [-e [ENTRY_POINT]] [-b BOOTROM] [-n ICOUNT] [-s] filename


positional arguments:
  filename              The binary (.bin or .uf2) file to execute in the emulator

options:
  -h, --help            show this help message and exit
  -e [ENTRY_POINT], --entry_point [ENTRY_POINT]
                        The entry point for execution in hex format (eg.
                        0x10000354). Defaults to 0x10000000 if no bootrom is
                        loaded.
  -b BOOTROM, --bootrom BOOTROM
                        The binary (.bin) file that holds the bootrom code.
                        Defaults to bootrom.bin
  -n ICOUNT, --icount ICOUNT
                        Limit the number of instructions to execute
  -s, --step            Enable stepping per instruction
```

or with the integrated GDB server:
```bash
usage: gdbserver.py [-h] [-e [ENTRY_POINT]] [-b BOOTROM] [-S SERIAL] filename


positional arguments:
  filename              The binary (.bin or .uf2) file to execute in the emulator

options:
  -h, --help            show this help message and exit
  -e [ENTRY_POINT], --entry_point [ENTRY_POINT]
                        The entry point for execution in hex format (eg. 0x10000354). Defaults to 0x10000000 if no bootrom is loaded.
  -b BOOTROM, --bootrom BOOTROM
                        The binary (.bin) file that holds the bootrom code. Defaults to bootrom.bin
  -S SERIAL, --serial SERIAL
                        Use serial port for UART0. Specify serial port device (e.g /dev/ttyp1)
```