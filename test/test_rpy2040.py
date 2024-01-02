from rpy2040.rpy2040 import Rp2040, SRAM_START, IGNORE_BL, add_with_carry
import util.assembler as asm

SP_START = 0x20000100


class TestInstructions:

    def test_push(self):
        rp = Rp2040()
        rp.sp = SP_START
        rp.registers[4] = 42
        rp.registers[5] = 43
        rp.registers[6] = 44
        rp.lr = 45
        rp.flash[0:2] = b'\x70\xb5'  # push	{r4, r5, r6, lr}
        rp.execute_instruction()
        assert rp.sp == SP_START - 16
        wordstring = b'*\x00\x00\x00+\x00\x00\x00,\x00\x00\x00-\x00\x00\x00'
        assert rp.sram[SP_START-SRAM_START-16:SP_START-SRAM_START] == wordstring

    def test_movs(self):
        rp = Rp2040()
        rp.flash[0:2] = b'\xd0\x24'  # movs	r4, #208
        rp.execute_instruction()
        assert rp.registers[4] == 208

    def test_lsls_immediate(self):
        rp = Rp2040()
        rp.registers[4] = 208
        rp.flash[0:2] = b'\x24\x06'  # lsls	r4, r4, #24
        rp.apsr_n = False
        rp.apsr_z = True
        rp.apsr_c = True
        rp.execute_instruction()
        assert rp.registers[4] == 3489660928
        assert rp.apsr_n is True
        assert rp.apsr_z is False
        assert rp.apsr_c is False

    def test_lsls_immediate_with_carry_out(self):
        rp = Rp2040()
        rp.registers[4] = 208
        rp.flash[0:2] = b'\x64\x06'  # lsls	r4, r4, #25
        rp.apsr_n = False
        rp.apsr_z = True
        rp.apsr_c = False
        rp.execute_instruction()
        assert rp.registers[4] == 2684354560
        assert rp.apsr_n is True
        assert rp.apsr_z is False
        assert rp.apsr_c is True

    def test_lsr_immediate(self):
        rp = Rp2040()
        rp.registers[4] = 0x00000074
        opcode = asm.opcodeLSRimm(rd=1, rm=4, imm5=3)
        rp.flash[0:len(opcode)] = opcode  # lsrs r1, r4, #3
        rp.execute_instruction()
        assert rp.registers[1] == 0x0000000e
        assert rp.apsr_n is False
        assert rp.apsr_z is False
        assert rp.apsr_c is True

    def test_bl(self):
        if IGNORE_BL:
            assert True
        else:
            rp = Rp2040()
            rp.pc = 0x10000360
            rp.flash[0x360:0x364] = b'\x00\xf0\x0a\xf8'  # bl	10000378
            rp.execute_instruction()
            assert rp.pc == 0x10000378
            assert rp.lr == 0x10000365

    def test_str_immediate(self):
        rp = Rp2040()
        rp.flash[0:2] = b'\x93\x62'  # str	r3, [r2, #40]
        rp.registers[3] = 0xcafe
        rp.registers[2] = SRAM_START
        rp.execute_instruction()
        assert rp.sram[40:44] == b'\xfe\xca\x00\x00'

    def test_ldr_literal(self):
        rp = Rp2040()
        rp.flash[0:2] = b'\x09\x4a'  # ldr	r2, [pc, #36]
        rp.flash[40:44] = (0x4001c004).to_bytes(4, 'little')
        rp.execute_instruction()
        assert rp.registers[2] == 0x4001c004

    def test_mov_register(self):
        rp = Rp2040()
        rp.flash[0:2] = b'\x94\x46'  # mov	ip, r2
        rp.registers[2] = 0x42
        rp.execute_instruction()
        assert rp.registers[12] == 0x42

    def test_add_register_t2(self):
        rp = Rp2040()
        rp.flash[0:2] = b'\x63\x44'  # add	r3, ip
        rp.registers[3] = 0x42
        rp.registers[12] = 0x69
        rp.execute_instruction()
        assert rp.registers[3] == 0x42 + 0x69

    def test_b_t2(self):
        rp = Rp2040()
        rp.pc = 0x10000376
        rp.flash[0x376:0x378] = b'\xf6\xe7'  # b.n	10000366
        rp.execute_instruction()
        assert rp.pc == 0x10000366

    def test_bx(self):
        rp = Rp2040()
        rp.pc = 0x10000376
        opcode = asm.opcodeBX(rm=asm.R2)  # bx r2
        rp.flash[0x376:0x378] = opcode
        rp.registers[2] = 0x20000043
        rp.execute_instruction()
        assert rp.pc == 0x20000042

    def test_ldr_immediate(self):
        rp = Rp2040()
        rp.pc = 0x10000374
        rp.flash[0x374:0x376] = b'\x93\x69'  # ldr r3, [r2, #24]
        rp.registers[2] = 0x40034000
        rp.mmu.regions['uart0'].uartfr = 0xcafebabe
        rp.execute_instruction()
        assert rp.registers[3] == 0xcafebabe

    def test_tst(self):
        rp = Rp2040()
        rp.flash[0:2] = b'\x19\x42'  # tst r1, r3
        rp.registers[1] = 0x42
        rp.registers[3] = 0x43
        rp.apsr_n = True
        rp.apsr_z = True
        rp.apsr_c = True
        rp.execute_instruction()
        assert rp.apsr_n is False
        assert rp.apsr_z is False
        assert rp.apsr_c is True

    def test_tst_negative(self):
        rp = Rp2040()
        rp.flash[0:2] = b'\x19\x42'  # tst	r1, r3
        rp.registers[1] = 0xf0000000
        rp.registers[3] = 0xf0000400
        rp.apsr_n = False
        rp.apsr_z = True
        rp.apsr_c = False
        rp.execute_instruction()
        assert rp.apsr_n is True
        assert rp.apsr_z is False
        assert rp.apsr_c is False

    def test_tst_zero(self):
        rp = Rp2040()
        rp.flash[0:2] = b'\x19\x42'  # tst	r1, r3
        rp.registers[1] = 0xf0000000
        rp.registers[3] = 0x0000f000
        rp.apsr_n = False
        rp.apsr_z = False
        rp.apsr_c = False
        rp.execute_instruction()
        assert rp.apsr_n is False
        assert rp.apsr_z is True
        assert rp.apsr_c is False

    def test_bne_not_equal(self):
        rp = Rp2040()
        rp.pc = 0x10000378
        rp.flash[0x378:0x37a] = b'\xfc\xd1'  # bne.n	10000374
        rp.apsr_z = False
        rp.execute_instruction()
        assert rp.pc == 0x10000374

    def test_ldrsh(self):
        rp = Rp2040()
        rp.flash[0:2] = b'\x5d\x5f'  # ldrsh	r5, [r3, r5]
        rp.sram[0x618:0x61A] = b'\xfe\xca'
        rp.registers[3] = 0x20000618
        rp.registers[5] = 0
        rp.execute_instruction()
        assert rp.registers[5] == 0x0000cafe

    def test_cmp_immediate(self):
        rp = Rp2040()
        rp.flash[0:2] = b'\x42\x2d'  # cmp	r5, #66	@ 0x42
        rp.registers[5] = 0x42
        rp.execute_instruction()
        assert rp.apsr_z is True
        assert rp.apsr_c is True
        assert rp.apsr_n is False
        assert rp.apsr_v is False

    def test_cmp_register(self):
        rp = Rp2040()
        rp.flash[0:2] = b'\xa5\x42'  # cmp	r5, r4
        rp.registers[4] = 0
        rp.registers[5] = 0x80000000
        rp.execute_instruction()
        assert rp.apsr_z is False
        assert rp.apsr_c is False
        assert rp.apsr_n is True
        assert rp.apsr_v is True

    def test_add_t2(self):
        rp = Rp2040()
        opcode = asm.opcodeADDT2(rdn=1, imm8=1)
        rp.flash[0:len(opcode)] = opcode  # adds r1, #1
        rp.registers[1] = 0xffffffff
        rp.execute_instruction()
        assert rp.registers[1] == 0
        assert rp.apsr_z is True
        assert rp.apsr_c is True
        assert rp.apsr_n is False
        assert rp.apsr_v is False

    def test_sub_t2(self):
        rp = Rp2040()
        opcode = asm.opcodeSUBT2(rdn=5, imm8=42)
        rp.flash[0:len(opcode)] = opcode  # subs r5, #42
        rp.registers[5] = 12
        rp.execute_instruction()
        assert rp.registers[5] == 0xffffffe2
        assert rp.apsr_z is False
        assert rp.apsr_c is False
        assert rp.apsr_n is True
        assert rp.apsr_v is False

    def test_rsb(self):
        rp = Rp2040()
        opcode = asm.opcodeRSB(rd=3, rn=2)
        rp.flash[0:len(opcode)] = opcode  # rsbs r3, r2, #0
        rp.registers[2] = 12
        rp.execute_instruction()
        assert rp.registers[3] == 0xfffffff4
        assert rp.apsr_z is False
        assert rp.apsr_c is False
        assert rp.apsr_n is True
        assert rp.apsr_v is False

    def test_ldrb_immediate(self):
        rp = Rp2040()
        opcode = asm.opcodeLDRBimm(1, 0, 0)
        rp.flash[0:len(opcode)] = opcode  # ldrb r1, [r0, #0]
        rp.sram[0x618:0x61A] = b'\xfe\xca'
        rp.registers[0] = 0x20000619
        rp.execute_instruction()
        assert rp.registers[1] == 0x000000ca

    def test_adc(self):
        rp = Rp2040()
        opcode = asm.opcodeADC(rdn=1, rm=4)
        rp.flash[0:len(opcode)] = opcode  # adcs r1, r4
        rp.apsr_c = True
        rp.registers[1] = 0xfffffff0
        rp.registers[4] = 0x0000000f
        rp.execute_instruction()
        assert rp.registers[1] == 0
        assert rp.apsr_z is True
        assert rp.apsr_c is True
        assert rp.apsr_n is False
        assert rp.apsr_v is False

    def test_uxtb(self):
        rp = Rp2040()
        opcode = asm.opcodeUXTB(rd=1, rm=3)
        rp.flash[0:len(opcode)] = opcode  # adcs r1, r4
        rp.registers[3] = 0x01020304
        rp.execute_instruction()
        assert rp.registers[1] == 0x00000004

    def test_ldm(self):
        rp = Rp2040()
        opcode = asm.opcodeLDM(rn=0, registers=(1, 2))
        rp.flash[0:len(opcode)] = opcode  # ldmia	r0!, {r1, r2}
        rp.registers[0] = 0x20000618
        rp.sram[0x618:0x618+8] = b'\xbe\xba\xfe\xca\x45\x44\x43\x42'
        rp.execute_instruction()
        assert rp.registers[1] == 0xcafebabe
        assert rp.registers[2] == 0x42434445
        assert rp.registers[0] == 0x20000618 + 8

    def test_msr_msp(self):
        rp = Rp2040()
        opcode = asm.opcodeMSR(spec_reg=asm.SYSM_MSP, rn=asm.R1)  # msr MSP, r1
        rp.flash[0:len(opcode)] = opcode
        rp.sp = 0
        rp.registers[1] = 0x2000061a
        rp.execute_instruction()
        assert rp.sp == 0x20000618

    def test_bic(self):
        rp = Rp2040()
        opcode = asm.opcodeBIC(rdn=asm.R0, rm=asm.R1)  # bics r0, r1
        rp.flash[0:2] = opcode
        rp.registers[0] = 0x42
        rp.registers[1] = 0x2
        rp.apsr_n = True
        rp.apsr_z = True
        rp.apsr_c = True
        rp.execute_instruction()
        assert rp.registers[0] == 0x40
        assert rp.apsr_n is False
        assert rp.apsr_z is False
        assert rp.apsr_c is True

    def test_bic_zero(self):
        rp = Rp2040()
        opcode = asm.opcodeBIC(rdn=asm.R0, rm=asm.R1)  # bics r0, r1
        rp.flash[0:2] = opcode
        rp.registers[0] = 0x2
        rp.registers[1] = 0x2
        rp.apsr_n = True
        rp.apsr_z = False
        rp.execute_instruction()
        assert rp.registers[0] == 0x0
        assert rp.apsr_n is False
        assert rp.apsr_z is True


class TestAddWithCarry:

    def test_subtract_no_flags(self):
        result, c, v = add_with_carry(0x00b71b00, ~0xb71b0000, True)
        assert result == 1234967296
        assert c is False
        assert v is False

    def test_add_no_flags(self):
        result, c, v = add_with_carry(200, 400, False)
        assert result == 600
        assert c is False
        assert v is False

    def test_add_carry_out(self):
        result, c, v = add_with_carry(0xFFFFFFFFFF, 1, False)
        assert result == 0
        assert c is True
        assert v is False

    def test_subtract_carry_out(self):
        result, c, v = add_with_carry(0xFFFFFFFFFF, ~0x00000008, True)
        assert result == 4294967287
        assert c is True
        assert v is False

    def test_subtract_overflow(self):
        result, c, v = add_with_carry(0, ~0x80000000, True)
        assert result == 2147483648
        assert c is False
        assert v is True
