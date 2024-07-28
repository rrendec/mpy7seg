# SPDX-License-Identifier: MIT

ADDR_NO_OP          = 0x00
ADDR_DIGIT_BASE     = 0x01
ADDR_DECODE_MODE    = 0x09
ADDR_INTENSITY      = 0x0a
ADDR_SCAN_LIMIT     = 0x0b
ADDR_SHUTDOWN       = 0x0c
ADDR_DISPLAY_TEST   = 0x0f

MAP_BUILTIN = {
    '0': 0x0, '1': 0x1, '2': 0x2, '3': 0x3,
    '4': 0x4, '5': 0x5, '6': 0x6, '7': 0x7,
    '8': 0x8, '9': 0x9, '-': 0xa, 'E': 0xb,
    'H': 0xc, 'L': 0xd, 'P': 0xe, ' ': 0xf,
}

MAP_EXTENDED = {
    '0': 0x7e, '1': 0x30, '2': 0x6d, '3': 0x79,
    '4': 0x33, '5': 0x5b, '6': 0x5f, '7': 0x70,
    '8': 0x7f, '9': 0x7b, 'A': 0x77, 'B': 0x1f,
    'C': 0x4e, 'D': 0x3d, 'E': 0x4f, 'F': 0x47,
    'a': 0x77, 'b': 0x1f, 'c': 0x0d, 'd': 0x3d,
    'e': 0x4f, 'f': 0x47, '-': 0x01, ' ': 0x00,
}

NUM_CHRS = 8

class MAX7219:
    def __init__(self, spi, cs, decode_mode=0, intensity=7, mirror=False):
        self._spi = spi
        self._cs = cs
        self._decode_mode = decode_mode
        self._intensity = intensity
        self._mirror = mirror
        self._buffer = bytearray(NUM_CHRS)
        self.init()

    def init(self):
        self.off()
        for digit in range(NUM_CHRS):
            self._write_reg(ADDR_DIGIT_BASE + digit, 0)
        self._write_decode_mode()
        self._write_reg(ADDR_INTENSITY, self._intensity)
        self._write_reg(ADDR_SCAN_LIMIT, NUM_CHRS - 1)
        self._write_reg(ADDR_DISPLAY_TEST, 0)
        self.on()

    def on(self):
        self._write_reg(ADDR_SHUTDOWN, 1)

    def off(self):
        self._write_reg(ADDR_SHUTDOWN, 0)

    def decode_mode(self, decode_mode=None):
        if decode_mode is not None:
            self._decode_mode = decode_mode
            self._write_decode_mode()
        return self._decode_mode

    def intensity(self, intensity=None):
        if intensity is not None:
            assert intensity >= 0x0 and intensity <= 0xf
            self._intensity = intensity
            self._write_reg(ADDR_INTENSITY, self._intensity)
        return self._intensity

    def mirror(self):
        return self._mirror

    def _write_reg(self, addr, val):
        self._cs.off()
        self._spi.write(bytearray([addr, val]))
        self._cs.on()

    def _write_decode_mode(self):
        val = self._decode_mode
        if self._mirror:
            val = (val & 0xf0) >> 4 | (val & 0x0f) << 4
            val = (val & 0xcc) >> 2 | (val & 0x33) << 2
            val = (val & 0xaa) >> 1 | (val & 0x55) << 1
        self._write_reg(ADDR_DECODE_MODE, val)

    def write_chr_raw(self, val, idx=0):
        assert idx >= 0 and idx < NUM_CHRS
        if self._mirror:
            idx = 7 - idx
        self._buffer[idx] = val
        self._write_reg(ADDR_DIGIT_BASE + idx, val)

    def write_chr_xlate(self, ch, idx=0, dot=False, strict=False):
        assert idx >= 0 and idx < NUM_CHRS
        if ch == '.':
            ch = ' '
            dot = True
        if self._decode_mode & (1 << idx) == 0:
            val = MAP_EXTENDED.get(ch, None)
            dfl = 0
        else:
            val = MAP_BUILTIN.get(ch, None)
            dfl = 0xf
        assert val is not None or not strict
        if val is None:
            val = dfl
        if dot:
            val |= 0x80
        self.write_chr_raw(val, idx)

    def write_str(self, s, idx=0, strict=False):
        buf = ''
        dot = [False] * NUM_CHRS
        for ch in s:
            if len(buf) >= NUM_CHRS:
                break
            if ch != '.':
                buf += ch
            elif len(buf) == 0 or dot[len(buf) - 1]:
                buf += ch
            else:
                dot[len(buf) - 1] = True
        for off in range(len(buf)):
            if idx + off >= NUM_CHRS:
                break
            self.write_chr_xlate(buf[off], idx + off, dot[off])

    def clear(self, start=0, length=NUM_CHRS):
        self.write_str(' ' * length, start)
