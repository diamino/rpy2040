import pytest
from rpy2040.rpy2040 import Rp2040, SRAM_START, IGNORE_BL

SP_START = 0x20000100


class TestExecuteInstruction:

    def test_push(self):
        rp = Rp2040(pc=0x10000000, sp=SP_START)
        rp.registers[4] = 42
        rp.registers[5] = 43
        rp.registers[6] = 44
        rp.lr = 45
        rp.flash[0:2] = b'\x70\xb5'  # push	{r4, r5, r6, lr}
        rp.execute_intstruction()
        assert rp.sp == SP_START - 16
        assert rp.sram[SP_START-SRAM_START-16:SP_START-SRAM_START] == b'*\x00\x00\x00+\x00\x00\x00,\x00\x00\x00-\x00\x00\x00'

    def test_movs(self):
        rp = Rp2040(pc=0x10000000)
        rp.flash[0:2] = b'\xd0\x24'  # movs	r4, #208
        rp.execute_intstruction()
        assert rp.registers[4] == 208

    def test_lsls_immediate(self):
        rp = Rp2040(pc=0x10000000)
        rp.registers[4] = 208
        rp.flash[0:2] = b'\x24\x06'  # lsls	r4, r4, #24
        rp.execute_intstruction()
        assert rp.registers[4] == 3489660928

    def test_bl(self):
        if IGNORE_BL:
            assert True
        else:
            rp = Rp2040(pc=0x10000360)
            rp.flash[0x360:0x364] = b'\x00\xf0\x0a\xf8'  # bl	10000378
            rp.execute_intstruction()
            assert rp.pc == 0x10000378

    def test_str_immediate(self):
        rp = Rp2040(pc=0x10000000)
        rp.flash[0:2] = b'\x93\x62'  # str	r3, [r2, #40]
        rp.registers[3] = 0xcafe
        rp.registers[2] = SRAM_START
        rp.execute_intstruction()
        assert rp.sram[40:44] == b'\xfe\xca\x00\x00'

    def test_ldr_literal(self):
        rp = Rp2040(pc=0x10000000)
        rp.flash[0:2] = b'\x09\x4a'  # ldr	r2, [pc, #36]
        rp.flash[40:44] = (0x4001c004).to_bytes(4, 'little')
        rp.execute_intstruction()
        assert rp.registers[2] == 0x4001c004

    def test_mov_register(self):
        rp = Rp2040(pc=0x10000000)
        rp.flash[0:2] = b'\x94\x46'  # mov	ip, r2
        rp.registers[2] = 0x42
        rp.execute_intstruction()
        assert rp.registers[12] == 0x42

    def test_add_register_t2(self):
        rp = Rp2040(pc=0x10000000)
        rp.flash[0:2] = b'\x63\x44'  # add	r3, ip
        rp.registers[3] = 0x42
        rp.registers[12] = 0x69
        rp.execute_intstruction()
        assert rp.registers[3] == 0x42 + 0x69

    def test_b_t2(self):
        rp = Rp2040(pc=0x10000376)
        rp.flash[0x376:0x378] = b'\xf6\xe7'  # b.n	10000366
        rp.execute_intstruction()
        assert rp.pc == 0x10000366

    def test_ldr_immediate(self):
        rp = Rp2040(pc=0x10000374)
        rp.flash[0x374:0x376] = b'\x93\x69'  # ldr	r3, [r2, #24]
        rp.registers[2] = 0x40034000
        rp.mmu.regions['uart0'].uartfr = 0xcafebabe
        rp.execute_intstruction()
        assert rp.registers[3] == 0xcafebabe

    def test_tst(self):
        rp = Rp2040(pc=0x10000000)
        rp.flash[0:2] = b'\x19\x42'  # tst	r1, r3
        rp.registers[1] = 0x42
        rp.registers[3] = 0x43
        rp.apsr_n = True
        rp.apsr_z = True
        rp.apsr_c = True
        rp.execute_intstruction()
        assert rp.apsr_n is False
        assert rp.apsr_z is False
        assert rp.apsr_c is True

    def test_tst_negative(self):
        rp = Rp2040(pc=0x10000000)
        rp.flash[0:2] = b'\x19\x42'  # tst	r1, r3
        rp.registers[1] = 0xf0000000
        rp.registers[3] = 0xf0000400
        rp.apsr_n = False
        rp.apsr_z = True
        rp.apsr_c = False
        rp.execute_intstruction()
        assert rp.apsr_n is True
        assert rp.apsr_z is False
        assert rp.apsr_c is False

    def test_tst_zero(self):
        rp = Rp2040(pc=0x10000000)
        rp.flash[0:2] = b'\x19\x42'  # tst	r1, r3
        rp.registers[1] = 0xf0000000
        rp.registers[3] = 0x0000f000
        rp.apsr_n = False
        rp.apsr_z = False
        rp.apsr_c = False
        rp.execute_intstruction()
        assert rp.apsr_n is False
        assert rp.apsr_z is True
        assert rp.apsr_c is False

    def test_bne_not_equal(self):
        rp = Rp2040(pc=0x10000378)
        rp.flash[0x378:0x37a] = b'\xfc\xd1'  # bne.n	10000374
        rp.apsr_z = False
        rp.execute_intstruction()
        assert rp.pc == 0x10000374
