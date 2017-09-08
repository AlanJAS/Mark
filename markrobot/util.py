import threading
import time
import os
import mark


class Iterator(threading.Thread):
    def __init__(self, board):
        super(Iterator, self).__init__()
        self.board = board
        self._execute = True

    def run(self):
        while self._execute:
            try:
                while self.board.bytes_available():
                    self.board.iterate()
                time.sleep(0.001)
            except:
                continue

    def stop(self):
        self._execute = False


class Port(object):
    """An 8-bit port on the board."""
    def __init__(self, board, port_number, num_pins=8):
        self.board = board
        self.port_number = port_number
        self.reporting = False

        self.pins = []
        for i in range(num_pins):
            pin_nr = i + self.port_number * 8
            self.pins.append(Pin(self.board, pin_nr, type=DIGITAL, port=self))

    def __str__(self):
        return "Digital Port %i on %s" % (self.port_number, self.board)

    def enable_reporting(self):
        """Enable reporting of values for the whole port."""
        self.reporting = True
        msg = chr(REPORT_DIGITAL + self.port_number)
        msg += chr(1)
        self.board.sp.write(msg)
        for pin in self.pins:
            if pin.mode == INPUT:
                pin.reporting = True # TODO Shouldn't this happen at the pin?

    def disable_reporting(self):
        """Disable the reporting of the port."""
        self.reporting = False
        msg = chr(REPORT_DIGITAL + self.port_number)
        msg += chr(0)
        self.board.sp.write(msg)

    def write(self):
        """Set the output pins of the port to the correct state."""
        mask = 0
        for pin in self.pins:
            if pin.mode == OUTPUT:
                if pin.value == 1:
                    pin_nr = pin.pin_number - self.port_number * 8
                    mask |= 1 << pin_nr
        msg = chr(DIGITAL_MESSAGE + self.port_number)
        msg += chr(mask % 128)
        msg += chr(mask >> 7)
        self.board.sp.write(msg)

    def _update(self, mask):
        """Update the values for the pins marked as input with the mask."""
        if self.reporting:
            for pin in self.pins:
                if pin.mode is INPUT:
                    pin_nr = pin.pin_number - self.port_number * 8
                    pin.value = (mask & (1 << pin_nr)) > 0

class Pin(object):
    """A Pin representation"""
    def __init__(self, board, pin_number, type=ANALOG, port=None, active=False):
        self.board = board
        self.pin_number = pin_number
        self.type = type
        self.port = port
        self.PWM_CAPABLE = False
        self._mode = (type == DIGITAL and OUTPUT or INPUT)
        self.reporting = False
        self.value = None
        self._active = active

    def __str__(self):
        type = {ANALOG : 'Analog', DIGITAL : 'Digital'}[self.type]
        return "%s pin %d" % (type, self.pin_number)

    def _set_mode(self, mode):
        if mode is UNAVAILABLE:
            self._mode = UNAVAILABLE
            return
        if self._mode is UNAVAILABLE:
            raise IOError("%s can not be used through Firmata." % self)
        if mode is PWM and not self.PWM_CAPABLE:
            raise IOError("%s does not have PWM capabilities." % self)
        if mode == SERVO:
            if self.type != DIGITAL:
                raise IOError("Only digital pins can drive servos! %s is not"
                    "digital." % self)
            self._mode = SERVO
            self.board.servo_config(self.pin_number)
            return

        # Set mode with SET_PIN_MODE message
        self._mode = mode
        command = chr(SET_PIN_MODE)
        command += chr(self.pin_number)
        command += chr(mode)
        self.board.sp.write(command)
        if mode == INPUT:
            self.enable_reporting()

    def _get_mode(self):
        return self._mode

    mode = property(_get_mode, _set_mode)
    """
    Mode of operation for the pin. Can be one of the pin modes: INPUT, OUTPUT,
    ANALOG, PWM. or SERVO (or UNAVAILABLE).
    """

    def enable_reporting(self):
        """Set an input pin to report values."""
        if self.mode is not INPUT:
            raise IOError, "%s is not an input and can therefore not report" % self
        if self.type == ANALOG:
            self.reporting = True
            msg = chr(REPORT_ANALOG + self.pin_number)
            msg += chr(1)
            self.board.sp.write(msg)
        else:
            self.port.enable_reporting() # TODO This is not going to work for non-optimized boards like Mega

    def disable_reporting(self):
        """Disable the reporting of an input pin."""
        if self.type == ANALOG:
            self.reporting = False
            msg = chr(REPORT_ANALOG + self.pin_number)
            msg += chr(0)
            self.board.sp.write(msg)
        else:
            self.port.disable_reporting() # TODO This is not going to work for non-optimized boards like Mega

    def read(self):
        """
        Returns the output value of the pin. This value is updated by the
        boards :meth:`Board.iterate` method. Value is always in the range from
        0.0 to 1.0.
        """
        if self.mode == UNAVAILABLE:
            raise IOError, "Cannot read pin %s"% self.__str__()
        return self.value

    def write(self, value):
        """
        Output a voltage from the pin

        :arg value: Uses value as a boolean if the pin is in output mode, or
            expects a float from 0 to 1 if the pin is in PWM mode. If the pin
            is in SERVO the value should be in degrees.

        """
        if self.mode is UNAVAILABLE:
            raise IOError, "%s can not be used through Firmata." % self
        if self.mode is INPUT:
            raise IOError, "%s is set up as an INPUT and can therefore not be written to" % self
        if value is not self.value:
            self.value = value
            if self.mode is OUTPUT:
                if self.port:
                    self.port.write()
                else:
                    msg = chr(DIGITAL_MESSAGE)
                    msg += chr(self.pin_number)
                    msg += chr(value)
                    self.board.sp.write(msg)
            elif self.mode is PWM:
                value = int(round(value * 255))
                msg = chr(ANALOG_MESSAGE + self.pin_number)
                msg += chr(value % 128)
                msg += chr(value >> 7)
                self.board.sp.write(msg)
            elif self.mode is SERVO:
                value = int(value)
                msg = chr(ANALOG_MESSAGE + self.pin_number)
                msg += chr(value % 128)
                msg += chr(value >> 7)
                self.board.sp.write(msg)


def to_two_bytes(integer):
    """
    Breaks an integer into two 7 bit bytes.

    >>> for i in range(32768):
    ...     val = to_two_bytes(i)
    ...     assert len(val) == 2
    ...
    >>> to_two_bytes(32767)
    ('\\x7f', '\\xff')
    >>> to_two_bytes(32768)
    Traceback (most recent call last):
        ...
    ValueError: Can't handle values bigger than 32767 (max for 2 bits)

    """
    if integer > 32767:
        raise ValueError, "Can't handle values bigger than 32767 (max for 2 bits)"
    return chr(integer % 128), chr(integer >> 7)

def from_two_bytes(bytes):
    """
    Return an integer from two 7 bit bytes.

    >>> for i in range(32766, 32768):
    ...     val = to_two_bytes(i)
    ...     ret = from_two_bytes(val)
    ...     assert ret == i
    ...
    >>> from_two_bytes(('\\xff', '\\xff'))
    32767
    >>> from_two_bytes(('\\x7f', '\\xff'))
    32767
    """
    lsb, msb = bytes
    try:
        # Usually bytes have been converted to integers with ord already
        return msb << 7 | lsb
    except TypeError:
        # But add this for easy testing
        # One of them can be a string, or both
        try:
            lsb = ord(lsb)
        except TypeError:
            pass
        try:
            msb = ord(msb)
        except TypeError:
            pass
        return msb << 7 | lsb

def two_byte_iter_to_str(bytes):
    """
    Return a string made from a list of two byte chars.

    >>> string, s = 'StandardFirmata', []
    >>> for i in string:
    ...   s.append(i)
    ...   s.append('\\x00')
    >>> two_byte_iter_to_str(s)
    'StandardFirmata'

    >>> string, s = 'StandardFirmata', []
    >>> for i in string:
    ...   s.append(ord(i))
    ...   s.append(ord('\\x00'))
    >>> two_byte_iter_to_str(s)
    'StandardFirmata'
    """
    bytes = list(bytes)
    chars = []
    while bytes:
        lsb = bytes.pop(0)
        try:
            msb = bytes.pop(0)
        except IndexError:
            msb = 0x00
        chars.append(chr(from_two_bytes((lsb, msb))))
    return ''.join(chars)

def str_to_two_byte_iter(string):
    """
    Return a iter consisting of two byte chars from a string.

    >>> string, iter = 'StandardFirmata', []
    >>> for i in string:
    ...   iter.append(i)
    ...   iter.append('\\x00')
    >>> assert iter == str_to_two_byte_iter(string)
     """
    bytes = []
    for char in string:
        bytes += list(to_two_bytes(ord(char)))
    return bytes

def break_to_bytes(value):
    """
    Breaks a value into values of less than 255 that form value when multiplied.
    (Or almost do so with primes)
    Returns a tuple

    >>> break_to_bytes(200)
    (200,)
    >>> break_to_bytes(800)
    (200, 4)
    >>> break_to_bytes(802)
    (2, 2, 200)
    """
    if value < 256:
        return (value,)
    c = 256
    least = (0, 255)
    for i in range(254):
        c -= 1
        rest = value % c
        if rest == 0 and value / c < 256:
            return (c, value / c)
        elif rest == 0 and value / c > 255:
            parts = list(break_to_bytes(value / c))
            parts.insert(0, c)
            return tuple(parts)
        else:
            if rest < least[1]:
                least = (c, rest)
    return (c, value / c)

