import util.assembler as asm


class TestAssembler:

    def test_opcodeADC(self):
        assert asm.opcodeADC(1, 4) == b'\x61\x41'

    def test_opcodeADDT2(self):
        assert asm.opcodeADDT2(1, 1) == b'\x01\x31'

    def test_opcodeLDRBimm(self):
        assert asm.opcodeLDRBimm(1, 0, 0) == b'\x01\x78'

    def test_opcodeNEG(self):
        assert asm.opcodeNEG(4, 1) == b'\x4c\x42'

    def test_opcodeRSB(self):
        assert asm.opcodeRSB(4, 1) == b'\x4c\x42'

    def test_opcodeSUBT2(self):
        assert asm.opcodeSUBT2(1, 13) == b'\x0d\x39'

    def test_opcodeUXTB(self):
        assert asm.opcodeUXTB(1, 1) == b'\xc9\xb2'
