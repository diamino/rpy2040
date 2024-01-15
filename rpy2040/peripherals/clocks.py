'''
Clocks implementation of the RPy2040 project
'''
from .mpu import MemoryRegionMap

# Clocks
CLOCKS_BASE = 0x40008000
# CLOCKS_SIZE = 0xc8
CLOCKS_SIZE = 0x4000
# Clocks registers
CLK_REF_CTRL = 0x30
CLK_REF_DIV = 0x34
CLK_REF_SELECTED = 0x38
CLK_SYS_CTRL = 0x3c
CLK_SYS_DIV = 0x40
CLK_SYS_SELECTED = 0x44
CLK_PERI_CTRL = 0x48
CLK_PERI_DIV = 0x4c  # This register seems to be missing from the RP2040 datasheet (a6fe703-clean)
CLK_USB_CTRL = 0x54
CLK_USB_DIV = 0x58
CLK_ADC_CTRL = 0x60
CLK_ADC_DIV = 0x64
CLK_RTC_CTRL = 0x6c
CLK_RTC_DIV = 0x70
# Clocks masks


class Clocks(MemoryRegionMap):

    def __init__(self, base_address: int = CLOCKS_BASE, size: int = CLOCKS_SIZE):
        super().__init__("Clocks", base_address, size, atomic_writes=True)
        self.ref_ctrl = 0
        self.sys_ctrl = 0
        self.peri_ctrl = 0
        self.usb_ctrl = 0
        self.adc_ctrl = 0
        self.rtc_ctrl = 0
        self.readhooks[CLK_REF_CTRL] = self.read_ref_ctrl
        self.readhooks[CLK_REF_DIV] = self.read_ref_div
        self.readhooks[CLK_REF_SELECTED] = self.read_ref_selected
        self.readhooks[CLK_SYS_CTRL] = self.read_sys_ctrl
        self.readhooks[CLK_SYS_DIV] = self.read_sys_div
        self.readhooks[CLK_SYS_SELECTED] = self.read_sys_selected
        self.readhooks[CLK_PERI_CTRL] = self.read_peri_ctrl
        self.readhooks[CLK_PERI_DIV] = self.read_peri_div
        self.readhooks[CLK_USB_CTRL] = self.read_usb_ctrl
        self.readhooks[CLK_USB_DIV] = self.read_usb_div
        self.readhooks[CLK_ADC_CTRL] = self.read_adc_ctrl
        self.readhooks[CLK_ADC_DIV] = self.read_adc_div
        self.readhooks[CLK_RTC_CTRL] = self.read_rtc_ctrl
        self.readhooks[CLK_RTC_DIV] = self.read_rtc_div
        self.writehooks[CLK_REF_CTRL] = self.write_ref_ctrl
        self.writehooks[CLK_SYS_CTRL] = self.write_sys_ctrl

    def read_ref_ctrl(self) -> int:
        return self.ref_ctrl

    def read_ref_div(self) -> int:
        return 1 << 8

    def read_ref_selected(self) -> int:
        return 1 << (self.ref_ctrl & 0x3)

    def read_sys_ctrl(self) -> int:
        return self.sys_ctrl

    def read_sys_div(self) -> int:
        return 1 << 8

    def read_sys_selected(self) -> int:
        return 1 << (self.sys_ctrl & 0x1)

    def read_peri_ctrl(self) -> int:
        return self.peri_ctrl

    def read_peri_div(self) -> int:
        return 1 << 8

    def read_usb_ctrl(self) -> int:
        return self.usb_ctrl

    def read_usb_div(self) -> int:
        return 1 << 8

    def read_adc_ctrl(self) -> int:
        return self.adc_ctrl

    def read_adc_div(self) -> int:
        return 1 << 8

    def read_rtc_ctrl(self) -> int:
        return self.rtc_ctrl

    def read_rtc_div(self) -> int:
        return 1 << 8

    def write_ref_ctrl(self, value: int) -> None:
        self.ref_ctrl = value

    def write_sys_ctrl(self, value: int) -> None:
        self.sys_ctrl = value
