import threading

import time
import os
import pybluefirmata

from boards import BOARDS



class Iterator(threading.Thread):
    def __init__(self, board):
        super(Iterator, self).__init__()
        self.board = board
        self._execute = True

    def run(self):
        while self._execute:
            try:
                self.board.iterate()
                time.sleep(0.001)
            except Exception, e:
                # catch 'error: Bad file descriptor'
                # iterate may be called while the serial port is being closed,
                # causing an "error: (9, 'Bad file descriptor')"
                if getattr(e, 'errno', None) == 9:
                    break
                try:
                    if e[0] == 9:
                        break
                except (TypeError, IndexError):
                    pass
                raise

    def stop(self):
        self._execute = False


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

