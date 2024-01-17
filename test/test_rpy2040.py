from rpy2040.rpy2040 import Rp2040, SRAM_START, add_with_carry
import util.assembler as asm

SP_START = 0x20000100


class TestInstructions:

    def test_adc(self):
        rp = Rp2040()
        opcode = asm.opcodeADC(rdn=1, rm=4)  # adcs r1, r4
        rp.flash[0:len(opcode)] = opcode
        rp.apsr_c = True
        rp.registers[1] = 0xfffffff0
        rp.registers[4] = 0x0000000f
        rp.execute_instruction()
        assert rp.registers[1] == 0
        assert rp.apsr_z is True
        assert rp.apsr_c is True
        assert rp.apsr_n is False
        assert rp.apsr_v is False

    def test_add_immediate_t1(self):
        rp = Rp2040()
        opcode = asm.opcodeADDimmT1(rd=asm.R3, rn=asm.R4, imm3=4)  # adds r3, r4, #4
        rp.flash[0:2] = opcode
        rp.registers[4] = 0x69
        rp.execute_instruction()
        assert rp.registers[3] == 0x6d
        assert rp.apsr_z is False
        assert rp.apsr_c is False
        assert rp.apsr_n is False
        assert rp.apsr_v is False

    def test_add_immediate_t2(self):
        rp = Rp2040()
        opcode = asm.opcodeADDimmT2(rdn=1, imm8=1)  # adds r1, #1
        rp.flash[0:len(opcode)] = opcode
        rp.registers[1] = 0xffffffff
        rp.execute_instruction()
        assert rp.registers[1] == 0
        assert rp.apsr_z is True
        assert rp.apsr_c is True
        assert rp.apsr_n is False
        assert rp.apsr_v is False

    def test_add_register_t1(self):
        rp = Rp2040()
        opcode = asm.opcodeADDregT1(rd=asm.R2, rn=asm.R4, rm=asm.R3)  # adds r2, r4, r3
        rp.flash[0:2] = opcode
        rp.registers[3] = 0x42
        rp.registers[4] = 0x69
        rp.execute_instruction()
        assert rp.registers[2] == 0x42 + 0x69
        assert rp.apsr_z is False
        assert rp.apsr_c is False
        assert rp.apsr_n is False
        assert rp.apsr_v is False

    def test_add_register_t1_negative(self):
        rp = Rp2040()
        opcode = asm.opcodeADDregT1(rd=asm.R2, rn=asm.R4, rm=asm.R3)  # adds r2, r4, r3
        rp.flash[0:2] = opcode
        rp.registers[3] = 0xf0000000
        rp.registers[4] = 0x69
        rp.execute_instruction()
        assert rp.registers[2] == 0xf0000069
        assert rp.apsr_z is False
        assert rp.apsr_c is False
        assert rp.apsr_n is True
        assert rp.apsr_v is False

    def test_add_register_t1_carry(self):
        rp = Rp2040()
        opcode = asm.opcodeADDregT1(rd=asm.R2, rn=asm.R4, rm=asm.R3)  # adds r2, r4, r3
        rp.flash[0:2] = opcode
        rp.registers[3] = 0xf0000000
        rp.registers[4] = 0x10000000
        rp.execute_instruction()
        assert rp.registers[2] == 0x0
        assert rp.apsr_z is True
        assert rp.apsr_c is True
        assert rp.apsr_n is False
        assert rp.apsr_v is False

    def test_add_register_t2(self):
        rp = Rp2040()
        opcode = asm.opcodeADDregT2(rdn=asm.R3, rm=asm.R12)  # add	r3, ip
        rp.flash[0:2] = opcode
        rp.registers[3] = 0x42
        rp.registers[12] = 0x69
        rp.execute_instruction()
        assert rp.registers[3] == 0x42 + 0x69

    def test_add_sp_immediate_t2(self):
        rp = Rp2040()
        opcode = asm.opcodeADDSPimmT2(imm7=3)  # add sp, #12
        rp.flash[0:len(opcode)] = opcode
        rp.sp = SP_START
        rp.execute_instruction()
        assert rp.sp == SP_START + 12

    def test_adr(self):
        rp = Rp2040()
        rp.pc = 0x10000200
        opcode = asm.opcodeADR(rd=asm.R4, imm8=13)  # add	r4, pc, #52
        rp.flash[0x200:0x200+len(opcode)] = opcode
        rp.execute_instruction()
        assert rp.registers[4] == 0x10000234

    def test_and(self):
        rp = Rp2040()
        opcode = asm.opcodeAND(rdn=asm.R3, rm=asm.R1)  # ands r3, r1
        rp.flash[0:len(opcode)] = opcode
        rp.registers[1] = 0x80000062
        rp.registers[3] = 0x80042040
        rp.execute_instruction()
        assert rp.registers[3] == 0x80000040
        assert rp.apsr_z is False
        assert rp.apsr_c is False
        assert rp.apsr_n is True
        assert rp.apsr_v is False

    def test_b_t2(self):
        rp = Rp2040()
        rp.pc = 0x10000376
        opcode = asm.opcodeBT2(imm11=-10)  # b.n	10000366
        rp.flash[0x376:0x378] = opcode
        rp.execute_instruction()
        assert rp.pc == 0x10000366

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

    def test_bl(self):
        rp = Rp2040()
        rp.pc = 0x10000360
        opcode = asm.opcodeBL(imm32=20)  # bl	10000378
        rp.flash[0x360:0x364] = opcode
        rp.execute_instruction()
        assert rp.pc == 0x10000378
        assert rp.lr == 0x10000365

    def test_blx(self):
        rp = Rp2040()
        rp.pc = 0x10000376
        opcode = asm.opcodeBLX(rm=asm.R1)  # blx r1
        rp.flash[0x376:0x378] = opcode
        rp.registers[1] = 0x20000043
        rp.execute_instruction()
        assert rp.pc == 0x20000042
        assert rp.lr == 0x10000379

    def test_bne_not_equal(self):
        rp = Rp2040()
        rp.pc = 0x10000378
        opcode = asm.opcodeBT1(cond=asm.NE, imm8=-4)  # bne.n	10000374
        rp.flash[0x378:0x37a] = opcode
        rp.apsr_z = False
        rp.execute_instruction()
        assert rp.pc == 0x10000374

    def test_bx(self):
        rp = Rp2040()
        rp.pc = 0x10000376
        opcode = asm.opcodeBX(rm=asm.R2)  # bx r2
        rp.flash[0x376:0x378] = opcode
        rp.registers[2] = 0x20000043
        rp.execute_instruction()
        assert rp.pc == 0x20000042

    def test_bx_lr(self):
        rp = Rp2040()
        rp.pc = 0x10000376
        opcode = asm.opcodeBX(rm=asm.LR)  # bx lr
        rp.flash[0x376:0x378] = opcode
        rp.lr = 0x20000043
        rp.execute_instruction()
        assert rp.pc == 0x20000042

    def test_cmp_immediate(self):
        rp = Rp2040()
        opcode = asm.opcodeCMPimm(rn=asm.R5, imm8=66)  # cmp	r5, #66	@ 0x42
        rp.flash[0:2] = opcode
        rp.registers[5] = 0x42
        rp.execute_instruction()
        assert rp.apsr_z is True
        assert rp.apsr_c is True
        assert rp.apsr_n is False
        assert rp.apsr_v is False

    def test_cmp_register(self):
        rp = Rp2040()
        opcode = asm.opcodeCMPregT1(rn=asm.R5, rm=asm.R4)  # cmp	r5, r4
        rp.flash[0:2] = opcode
        rp.registers[4] = 0
        rp.registers[5] = 0x80000000
        rp.execute_instruction()
        assert rp.apsr_z is False
        assert rp.apsr_c is True
        assert rp.apsr_n is True
        assert rp.apsr_v is False

    def test_cmp_register_zero(self):
        rp = Rp2040()
        opcode = asm.opcodeCMPregT1(rn=asm.R2, rm=asm.R3)  # cmp	r2, r3
        rp.flash[0:2] = opcode
        rp.registers[2] = 0x80000000
        rp.registers[3] = 0x80000000
        rp.execute_instruction()
        assert rp.apsr_z is True
        assert rp.apsr_c is True
        assert rp.apsr_n is False
        assert rp.apsr_v is False

    def test_eor(self):
        rp = Rp2040()
        opcode = asm.opcodeEOR(rdn=asm.R3, rm=asm.R4)  # eors r3, r4
        rp.flash[0:len(opcode)] = opcode
        rp.registers[3] = 0x00300742
        rp.registers[4] = 0x80142700
        rp.execute_instruction()
        assert rp.registers[3] == 0x80242042
        assert rp.apsr_z is False
        assert rp.apsr_c is False
        assert rp.apsr_n is True
        assert rp.apsr_v is False

    def test_ldm(self):
        rp = Rp2040()
        opcode = asm.opcodeLDM(rn=0, registers=(1, 2))  # ldmia	r0!, {r1, r2}
        rp.flash[0:len(opcode)] = opcode
        rp.registers[0] = 0x20000618
        rp.sram[0x618:0x618+8] = b'\xbe\xba\xfe\xca\x45\x44\x43\x42'
        rp.execute_instruction()
        assert rp.registers[1] == 0xcafebabe
        assert rp.registers[2] == 0x42434445
        assert rp.registers[0] == 0x20000618 + 8

    def test_ldr_immediate_t1(self):
        rp = Rp2040()
        rp.pc = 0x10000374
        opcode = asm.opcodeLDRimmT1(rt=asm.R3, rn=asm.R2, imm5=6)  # ldr r3, [r2, #24]
        rp.flash[0x374:0x376] = opcode
        rp.registers[2] = 0x40034000
        rp.mpu.regions['uart0'].uartfr = 0xcafebabe
        rp.execute_instruction()
        assert rp.registers[3] == 0xcafebabe

    def test_ldr_immediate_t2(self):
        rp = Rp2040()
        opcode = asm.opcodeLDRimmT2(rt=3, imm8=6)  # ldr r3, [sp, #24]
        rp.flash[0:2] = opcode
        rp.sp = SP_START
        rp.sram[SP_START-SRAM_START+24:SP_START-SRAM_START+28] = b'\x0d\xf0\xfe\xca'
        rp.execute_instruction()
        assert rp.registers[3] == 0xcafef00d

    def test_ldr_literal(self):
        rp = Rp2040()
        opcode = asm.opcodeLDRlit(rt=asm.R2, imm8=9)  # ldr	r2, [pc, #36]
        rp.flash[0:2] = opcode
        rp.flash[40:44] = (0x4001c004).to_bytes(4, 'little')
        rp.execute_instruction()
        assert rp.registers[2] == 0x4001c004

    def test_ldrb_immediate(self):
        rp = Rp2040()
        opcode = asm.opcodeLDRBimm(1, 0, 0)  # ldrb r1, [r0, #0]
        rp.flash[0:len(opcode)] = opcode
        rp.sram[0x618:0x61A] = b'\xfe\xca'
        rp.registers[0] = 0x20000619
        rp.execute_instruction()
        assert rp.registers[1] == 0x000000ca

    def test_ldrsh(self):
        rp = Rp2040()
        rp.flash[0:2] = b'\x5d\x5f'  # ldrsh	r5, [r3, r5]
        rp.sram[0x618:0x61A] = b'\xfe\xca'
        rp.registers[3] = 0x20000618
        rp.registers[5] = 0
        rp.execute_instruction()
        assert rp.registers[5] == 0x0000cafe

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

    def test_mov_immediate(self):
        rp = Rp2040()
        rp.flash[0:2] = b'\xd0\x24'  # movs	r4, #208
        rp.execute_instruction()
        assert rp.registers[4] == 208

    def test_mov_register(self):
        rp = Rp2040()
        rp.flash[0:2] = b'\x94\x46'  # mov	ip, r2
        rp.registers[2] = 0x42
        rp.execute_instruction()
        assert rp.registers[12] == 0x42

    def test_msr_msp(self):
        rp = Rp2040()
        opcode = asm.opcodeMSR(spec_reg=asm.SYSM_MSP, rn=asm.R1)  # msr MSP, r1
        rp.flash[0:len(opcode)] = opcode
        rp.sp = 0
        rp.registers[1] = 0x2000061a
        rp.execute_instruction()
        assert rp.sp == 0x20000618

    def test_mvn(self):
        rp = Rp2040()
        opcode = asm.opcodeMVN(rd=asm.R3, rm=asm.R1)  # mvns r3, r1
        rp.flash[0:len(opcode)] = opcode
        rp.registers[1] = 0x5690fc3a
        rp.execute_instruction()
        assert rp.registers[3] == 0xa96f03c5
        assert rp.apsr_z is False
        assert rp.apsr_c is False
        assert rp.apsr_n is True
        assert rp.apsr_v is False

    def test_orr(self):
        rp = Rp2040()
        opcode = asm.opcodeORR(rdn=3, rm=0)  # orrs r3, r0
        rp.flash[0:len(opcode)] = opcode
        rp.registers[0] = 0x00000042
        rp.registers[3] = 0x80042000
        rp.execute_instruction()
        assert rp.registers[3] == 0x80042042
        assert rp.apsr_z is False
        assert rp.apsr_c is False
        assert rp.apsr_n is True
        assert rp.apsr_v is False

    def test_pop(self):
        rp = Rp2040()
        opcode = asm.opcodePOP(registers=(asm.R0, asm.R1, asm.PC))  # pop	{r0, r1, pc}
        rp.flash[0:2] = opcode
        wordstring = b'\x42\x00\x00\x00\x01\x00\x00\x00\xc7\x00\x00\x10'
        rp.sram[SP_START-SRAM_START-12:SP_START-SRAM_START] = wordstring
        rp.sp = SP_START - 12
        rp.execute_instruction()
        assert rp.sp == SP_START
        assert rp.pc == 0x100000c6
        assert rp.registers[0] == 0x42
        assert rp.registers[1] == 0x01

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

    def test_stm(self):
        rp = Rp2040()
        opcode = asm.opcodeSTM(rn=asm.R1, registers=(asm.R0, asm.R2))  # stmia	r1!, {r0, r2}
        rp.flash[0:len(opcode)] = opcode
        rp.registers[1] = 0x20000618
        rp.registers[0] = 0xcafebabe
        rp.registers[2] = 0x42434445
        rp.execute_instruction()
        assert rp.sram[0x618:0x618+8] == b'\xbe\xba\xfe\xca\x45\x44\x43\x42'
        assert rp.registers[1] == 0x20000618 + 8

    def test_str_immediate(self):
        rp = Rp2040()
        rp.flash[0:2] = b'\x93\x62'  # str	r3, [r2, #40]
        rp.registers[3] = 0xcafe
        rp.registers[2] = SRAM_START
        rp.execute_instruction()
        assert rp.sram[40:44] == b'\xfe\xca\x00\x00'

    def test_str_immediate_t2(self):
        rp = Rp2040()
        opcode = asm.opcodeSTRimmT2(rt=asm.R3, imm8=2)  # str r3, [sp, #8]
        rp.flash[0:2] = opcode
        rp.sp = SP_START
        rp.registers[3] = 0xcafef00d
        rp.execute_instruction()
        assert rp.sram[SP_START-SRAM_START+8:SP_START-SRAM_START+12] == b'\x0d\xf0\xfe\xca'

    def test_str_register(self):
        rp = Rp2040()
        opcode = asm.opcodeSTRreg(rt=asm.R1, rn=asm.R3, rm=asm.R2)  # str r1, [r3, r2]
        rp.flash[0:2] = opcode
        rp.registers[1] = 0xcafe
        rp.registers[2] = 0x28
        rp.registers[3] = SRAM_START
        rp.execute_instruction()
        assert rp.sram[40:44] == b'\xfe\xca\x00\x00'

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

    def test_sub_sp(self):
        rp = Rp2040()
        opcode = asm.opcodeSUBSP(imm7=2)  # sub sp, #8
        rp.flash[0:len(opcode)] = opcode
        rp.sp = SP_START
        rp.execute_instruction()
        assert rp.sp == SP_START - 8

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

    def test_uxtb(self):
        rp = Rp2040()
        opcode = asm.opcodeUXTB(rd=1, rm=3)
        rp.flash[0:len(opcode)] = opcode  # adcs r1, r4
        rp.registers[3] = 0x01020304
        rp.execute_instruction()
        assert rp.registers[1] == 0x00000004


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
