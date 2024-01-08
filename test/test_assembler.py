import util.assembler as asm


class TestAssembler:

    def test_opcodeADC(self):
        assert asm.opcodeADC(asm.R1, asm.R4) == b'\x61\x41'

    def test_opcodeADDT2(self):
        assert asm.opcodeADDT2(asm.R1, 1) == b'\x01\x31'

    def test_opcodeADR(self):
        assert asm.opcodeADR(asm.R4, 13) == b'\x0d\xa4'

    def test_opcodeBIC(self):
        assert asm.opcodeBIC(asm.R0, asm.R1) == b'\x88\x43'

    def test_opcodeBLX(self):
        assert asm.opcodeBLX(asm.R1) == b'\x88\x47'

    def test_opcodeBX(self):
        assert asm.opcodeBX(asm.R2) == b'\x10\x47'

    def test_opcodeLDM(self):
        assert asm.opcodeLDM(asm.R0, (asm.R1, asm.R2)) == b'\x06\xc8'

    def test_opcodeLDRimmT2(self):
        assert asm.opcodeLDRimmT2(asm.R3, 6) == b'\x06\x9b'

    def test_opcodeLDRBimm(self):
        assert asm.opcodeLDRBimm(asm.R1, asm.R0, 0) == b'\x01\x78'

    def test_opcodeLSRimm(self):
        assert asm.opcodeLSRimm(asm.R1, asm.R1, 1) == b'\x49\x08'

    def test_opcodeMSR(self):
        assert asm.opcodeMSR(asm.SYSM_MSP, asm.R1) == b'\x81\xf3\x08\x88'

    def test_opcodeNEG(self):
        assert asm.opcodeNEG(asm.R4, asm.R1) == b'\x4c\x42'

    def test_opcodeORR(self):
        assert asm.opcodeORR(asm.R3, asm.R0) == b'\x03\x43'

    def test_opcodePOP(self):
        assert asm.opcodePOP((asm.R0, asm.R1, asm.PC)) == b'\x03\xbd'

    def test_opcodeRSB(self):
        assert asm.opcodeRSB(asm.R4, asm.R1) == b'\x4c\x42'

    def test_opcodeSTM(self):
        assert asm.opcodeSTM(asm.R1, (asm.R0,)) == b'\x01\xc1'

    def test_opcodeSTRimmT2(self):
        assert asm.opcodeSTRimmT2(asm.R3, 0) == b'\x00\x93'

    def test_opcodeSTRreg(self):
        assert asm.opcodeSTRreg(asm.R1, asm.R3, asm.R2) == b'\x99\x50'

    def test_opcodeSUBT2(self):
        assert asm.opcodeSUBT2(asm.R1, 13) == b'\x0d\x39'

    def test_opcodeSUBSP(self):
        assert asm.opcodeSUBSP(2) == b'\x82\xb0'

    def test_opcodeUXTB(self):
        assert asm.opcodeUXTB(asm.R1, asm.R1) == b'\xc9\xb2'
