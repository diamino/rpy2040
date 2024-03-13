from rpy2040.peripherals.cortexreg import CortexRegisters, NVIC_IPR_BASE


class TestCortexRegisters:

    def test_nvic_priority_set(self):
        cortexreg = CortexRegisters()
        for i in range(4):
            cortexreg.write(NVIC_IPR_BASE + (i * 8), 0x40C00080)
            cortexreg.write(NVIC_IPR_BASE + (i * 8) + 4, 0x80C04000)
        assert cortexreg.interrupt_levels[0] == 0x12121212
        assert cortexreg.interrupt_levels[1] == 0x28282828
        assert cortexreg.interrupt_levels[2] == 0x81818181
        assert cortexreg.interrupt_levels[3] == 0x44444444

    def test_nvic_priority_read(self):
        cortexreg = CortexRegisters()
        cortexreg.interrupt_levels[0] = 0x12121212
        cortexreg.interrupt_levels[1] = 0x28282828
        cortexreg.interrupt_levels[2] = 0x41414141
        cortexreg.interrupt_levels[3] = 0x84848484
        for i in range(4):
            assert cortexreg.read(NVIC_IPR_BASE + (i * 8)) == 0x40C00080
            assert cortexreg.read(NVIC_IPR_BASE + (i * 8) + 4) == 0xC0804000
