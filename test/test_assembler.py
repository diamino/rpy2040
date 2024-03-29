import util.assembler as asm


class TestAssembler:

    def test_opcodeADC(self):
        assert asm.opcodeADC(asm.R1, asm.R4) == b'\x61\x41'

    def test_opcodeADDimmT1(self):
        assert asm.opcodeADDimmT1(asm.R3, asm.R4, 4) == b'\x23\x1d'

    def test_opcodeADDimmT2(self):
        assert asm.opcodeADDimmT2(asm.R1, 1) == b'\x01\x31'

    def test_opcodeADDregT1(self):
        assert asm.opcodeADDregT1(asm.R2, asm.R4, asm.R3) == b'\xe2\x18'

    def test_opcodeADDregT2(self):
        assert asm.opcodeADDregT2(asm.R3, asm.R12) == b'\x63\x44'

    def test_opcodeADDSPimmT1(self):
        assert asm.opcodeADDSPimmT1(asm.R4, 3) == b'\x03\xac'

    def test_opcodeADDSPimmT2(self):
        assert asm.opcodeADDSPimmT2(3) == b'\x03\xb0'

    def test_opcodeADR(self):
        assert asm.opcodeADR(asm.R4, 13) == b'\x0d\xa4'

    def test_opcodeAND(self):
        assert asm.opcodeAND(asm.R3, asm.R2) == b'\x13\x40'

    def test_opcodeASRimm(self):
        assert asm.opcodeASRimm(asm.R3, asm.R1, 2) == b'\x8b\x10'

    def test_opcodeBT1(self):
        assert asm.opcodeBT1(cond=asm.NE, imm8=-4) == b'\xfc\xd1'

    def test_opcodeBT2(self):
        assert asm.opcodeBT2(imm11=-10) == b'\xf6\xe7'

    def test_opcodeBIC(self):
        assert asm.opcodeBIC(asm.R0, asm.R1) == b'\x88\x43'

    def test_opcodeBKPT(self):
        assert asm.opcodeBKPT(42) == b'\x2a\xbe'

    def test_opcodeBL(self):
        assert asm.opcodeBL(20) == b'\x00\xf0\x0a\xf8'

    def test_opcodeBLX(self):
        assert asm.opcodeBLX(asm.R1) == b'\x88\x47'

    def test_opcodeBX(self):
        assert asm.opcodeBX(asm.R2) == b'\x10\x47'

    def test_opcodeCMPimm(self):
        assert asm.opcodeCMPimm(asm.R5, 66) == b'\x42\x2d'

    def test_opcodeCMPregT1(self):
        assert asm.opcodeCMPregT1(asm.R5, asm.R4) == b'\xa5\x42'

    def test_opcodeCMPregT2(self):
        assert asm.opcodeCMPregT2(asm.R7, asm.R8) == b'\x47\x45'

    def test_opcodeCPS(self):
        assert asm.opcodeCPS(asm.CPS_ID) == b'\x72\xb6'

    def test_opcodeDMB(self):
        assert asm.opcodeDMB(asm.DMB_SY) == b'\xbf\xf3\x5f\x8f'

    def test_opcodeEOR(self):
        assert asm.opcodeEOR(asm.R1, asm.R2) == b'\x51\x40'

    def test_opcodeLDM(self):
        assert asm.opcodeLDM(asm.R0, (asm.R1, asm.R2)) == b'\x06\xc8'

    def test_opcodeLDRimmT1(self):
        assert asm.opcodeLDRimmT1(asm.R3, asm.R2, 6) == b'\x93\x69'

    def test_opcodeLDRimmT2(self):
        assert asm.opcodeLDRimmT2(asm.R3, 6) == b'\x06\x9b'

    def test_opcodeLDRlit(self):
        assert asm.opcodeLDRlit(asm.R2, 9) == b'\x09\x4a'

    def test_opcodeLDRreg(self):
        assert asm.opcodeLDRreg(asm.R0, asm.R0, asm.R3) == b'\xc0\x58'

    def test_opcodeLDRBimm(self):
        assert asm.opcodeLDRBimm(asm.R1, asm.R0, 0) == b'\x01\x78'

    def test_opcodeLDRBreg(self):
        assert asm.opcodeLDRBreg(asm.R3, asm.R1, asm.R2) == b'\x8b\x5c'

    def test_opcodeLDRHimm(self):
        assert asm.opcodeLDRHimm(asm.R0, asm.R3, 0) == b'\x18\x88'

    def test_opcodeLDRSBreg(self):
        assert asm.opcodeLDRSBreg(asm.R3, asm.R1, asm.R2) == b'\x8b\x56'

    def test_opcodeLSRimm(self):
        assert asm.opcodeLSRimm(asm.R1, asm.R1, 1) == b'\x49\x08'

    def test_opcodeLSRreg(self):
        assert asm.opcodeLSRreg(asm.R6, asm.R7) == b'\xfe\x40'

    def test_opcodeMSR(self):
        assert asm.opcodeMSR(asm.SYSM_MSP, asm.R1) == b'\x81\xf3\x08\x88'

    def test_opcodeMRS(self):
        assert asm.opcodeMRS(asm.R12, asm.SYSM_PRIMASK) == b'\xef\xf3\x10\x8c'

    def test_opcodeMUL(self):
        assert asm.opcodeMUL(asm.R6, asm.R4) == b'\x66\x43'

    def test_opcodeMVN(self):
        assert asm.opcodeMVN(asm.R3, asm.R3) == b'\xdb\x43'

    def test_opcodeNEG(self):
        assert asm.opcodeNEG(asm.R4, asm.R1) == b'\x4c\x42'

    def test_opcodeORR(self):
        assert asm.opcodeORR(asm.R3, asm.R0) == b'\x03\x43'

    def test_opcodePOP(self):
        assert asm.opcodePOP((asm.R0, asm.R1, asm.PC)) == b'\x03\xbd'

    def test_opcodeREV(self):
        assert asm.opcodeREV(asm.R3, asm.R1) == b'\x0b\xba'

    def test_opcodeRSB(self):
        assert asm.opcodeRSB(asm.R4, asm.R1) == b'\x4c\x42'

    def test_opcodeSEV(self):
        assert asm.opcodeSEV() == b'\x40\xbf'

    def test_opcodeSBC(self):
        assert asm.opcodeSBC(asm.R0, asm.R3) == b'\x98\x41'

    def test_opcodeSTM(self):
        assert asm.opcodeSTM(asm.R1, (asm.R0,)) == b'\x01\xc1'

    def test_opcodeSTRimmT2(self):
        assert asm.opcodeSTRimmT2(asm.R3, 0) == b'\x00\x93'

    def test_opcodeSTRreg(self):
        assert asm.opcodeSTRreg(asm.R1, asm.R3, asm.R2) == b'\x99\x50'

    def test_opcodeSTRBimm(self):
        assert asm.opcodeSTRBimm(asm.R3, asm.R0, 29) == b'\x43\x77'

    def test_opcodeSTRBreg(self):
        assert asm.opcodeSTRBreg(asm.R3, asm.R0, asm.R2) == b'\x83\x54'

    def test_opcodeSTRHimm(self):
        assert asm.opcodeSTRHimm(asm.R3, asm.R0, 11) == b'\xc3\x82'

    def test_opcodeSTRHreg(self):
        assert asm.opcodeSTRHreg(asm.R1, asm.R3, asm.R2) == b'\x99\x52'

    def test_opcodeSUBT1(self):
        assert asm.opcodeSUBT1(asm.R7, asm.R1, 0) == b'\x0f\x1e'

    def test_opcodeSUBT2(self):
        assert asm.opcodeSUBT2(asm.R1, 13) == b'\x0d\x39'

    def test_opcodeSUBreg(self):
        assert asm.opcodeSUBreg(asm.R6, asm.R6, asm.R5) == b'\x76\x1b'

    def test_opcodeSUBSP(self):
        assert asm.opcodeSUBSP(2) == b'\x82\xb0'

    def test_opcodeSXTB(self):
        assert asm.opcodeSXTB(asm.R2, asm.R2) == b'\x52\xb2'

    def test_opcodeUXTB(self):
        assert asm.opcodeUXTB(asm.R1, asm.R1) == b'\xc9\xb2'

    def test_opcodeUXTH(self):
        assert asm.opcodeUXTH(asm.R3, asm.R2) == b'\x93\xb2'

    def test_opcodeWFE(self):
        assert asm.opcodeWFE() == b'\x20\xbf'
