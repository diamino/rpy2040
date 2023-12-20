# RPy2040

RP2040 chip emulator written in Python

The code is loosely based on the [rp2040js code](https://github.com/wokwi/rp2040js) from the [excellent live coding series](https://youtube.com/playlist?list=PLLomdjsHtJTxT-vdJHwa3z62dFXZnzYBm&si=1AcioLyIXY0Y92L1) by Uri Shaked of [Wokwi](https://wokwi.com).

The tags in the repository (loosely) refer to the resulting code after each episode of the live coding series.

## Requirements

* Python 3 (tested on v3.11.3)
* Pytest to run the tests

You have to supply your own compiled binaries (for RP2040) to be executed.

## Usage

```bash
python rpy2040.py [-h] filename [entry_point]

positional arguments:
  filename     The binary (.bin) file to execute in the emulator
  entry_point  The entry point for execution in hex format (eg. 0x10000354). Defaults to 0x10000000

options:
  -h, --help   show this help message and exit
```