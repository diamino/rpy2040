'''
Timer implementation of the RPy2040 project
'''
import time
from .mpu import MemoryRegionMap

# Timer
TIMER_BASE = 0x40054000
TIMER_SIZE = 0x44
# Timer registers
TIMEHR = 0x08
TIMELR = 0x0c
TIMERAWH = 0x24
TIMERAWL = 0x28
# Timer masks
ALARM_0 = 1 << 0
ALARM_1 = 1 << 1
ALARM_2 = 1 << 2
ALARM_3 = 1 << 3


class Timer(MemoryRegionMap):

    def __init__(self, base_address: int = TIMER_BASE, size: int = TIMER_SIZE):
        super().__init__("Timer", base_address, size)
        self.latchedtimehigh = 0
        self.readhooks[TIMEHR] = self.read_timehr
        self.readhooks[TIMELR] = self.read_timelr
        self.readhooks[TIMERAWH] = self.read_timerawh
        self.readhooks[TIMERAWL] = self.read_timerawl

    def read_timehr(self) -> int:
        return self.latchedtimehigh

    def read_timelr(self) -> int:
        latchedtime = time.time_ns() // 1000
        self.latchedtimehigh = (latchedtime >> 32) & 0xffffffff
        return latchedtime & 0xffffffff

    def read_timerawh(self) -> int:
        return ((time.time_ns() // 1000) >> 32) & 0xffffffff

    def read_timerawl(self) -> int:
        return (time.time_ns() // 1000) & 0xffffffff
