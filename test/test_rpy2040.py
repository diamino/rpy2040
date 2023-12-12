import pytest
from rpy2040.rpy2040 import Rp2040, SRAM_START

SP_START = 0x20000100


class TestExecuteInstruction:

    def test_0_push(self):
        rp = Rp2040(pc=0x10000000, sp=SP_START)
        rp.registers[4] = 42
        rp.registers[5] = 43
        rp.registers[6] = 44
        rp.lr = 45
        rp.flash[0:2] = b'\x70\xb5'  # push	{r4, r5, r6, lr}
        rp.execute_intstruction()
        assert rp.sp == SP_START - 16
        assert rp.sram[SP_START-SRAM_START-16:SP_START-SRAM_START] == b'*\x00\x00\x00+\x00\x00\x00,\x00\x00\x00-\x00\x00\x00'

    def test_1_movs(self):
        rp = Rp2040(pc=0x10000000)
        rp.flash[0:2] = b'\xd0\x24'  # movs	r4, #208
        rp.execute_intstruction()
        assert rp.registers[4] == 208

    def test_2_lsls_immediate(self):
        rp = Rp2040(pc=0x10000000)
        rp.registers[4] = 208
        rp.flash[0:2] = b'\x24\x06'  # lsls	r4, r4, #24
        rp.execute_intstruction()
        assert rp.registers[4] == 3489660928

    def test_3_bl(self):
        rp = Rp2040(pc=0x10000360)
        rp.flash[0x360:0x364] = b'\x00\xf0\x0a\xf8'  # bl	10000378
        rp.execute_intstruction()
        assert rp.pc == 0x10000378

    def test_4_str_immediate(self):
        rp = Rp2040(pc=0x10000000)
        rp.flash[0:2] = b'\x93\x62'  # str	r3, [r2, #40]
        rp.registers[3] = 0xcafe
        rp.registers[2] = SRAM_START
        rp.execute_intstruction()
        assert rp.sram[40:44] == b'\xfe\xca\x00\x00'

    def test_5_ldr_literal(self):
        rp = Rp2040(pc=0x10000000)
        rp.flash[0:2] = b'\x09\x4a'  # ldr	r2, [pc, #36]
        rp.flash[40:44] = (0x4001c004).to_bytes(4, 'little')
        rp.execute_intstruction()
        assert rp.registers[2] == 0x4001c004

    def test_6_mov_register(self):
        rp = Rp2040(pc=0x10000000)
        rp.flash[0:2] = b'\x94\x46'  # mov	ip, r2
        rp.registers[2] = 0x42
        rp.execute_intstruction()
        assert rp.registers[12] == 0x42
