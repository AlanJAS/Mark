#!/usr/bin/env python

# portable serial port access with python

# This is a module that gathers a list of serial ports on POSIXy systems.
# For some specific implementations, see also list_ports_linux, list_ports_osx
#
# this is a wrapper module for different platform implementations of the
# port enumeration feature
#
# (C) 2011-2013 Chris Liechti <cliechti@gmx.net>
# this is distributed under a free software license, see license.txt

"""\
The ``comports`` function is expected to return an iterable that yields tuples
of 3 strings: port name, human readable description and a hardware ID.

As currently no method is known to get the second two strings easily, they are
currently just identical to the port name.
"""

import glob
import sys
import os

from serial.tools.list_ports_linux import comports

# test
if __name__ == '__main__':
    for port, desc, hwid in sorted(comports()):
        print "%s: %s [%s]" % (port, desc, hwid)
