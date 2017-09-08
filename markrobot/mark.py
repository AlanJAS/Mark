import serial
import inspect
import time
import itertools
from util import two_byte_iter_to_str, to_two_bytes

# Message command bytes - straight from Firmata.h
DIGITAL_MESSAGE = 0x90      # send data for a digital pin
ANALOG_MESSAGE = 0xE0       # send data for an analog pin (or PWM)
DIGITAL_PULSE = 0x91        # SysEx command to send a digital pulse

# PULSE_MESSAGE = 0xA0      # proposed pulseIn/Out msg (SysEx)
# SHIFTOUT_MESSAGE = 0xB0   # proposed shiftOut msg (SysEx)
REPORT_ANALOG = 0xC0        # enable analog input by pin #
REPORT_DIGITAL = 0xD0       # enable digital input by port pair
START_SYSEX = 0xF0          # start a MIDI SysEx msg
SET_PIN_MODE = 0xF4         # set a pin to INPUT/OUTPUT/PWM/etc
END_SYSEX = 0xF7            # end a MIDI SysEx msg
REPORT_VERSION = 0xF9       # report firmware version
SYSTEM_RESET = 0xFF         # reset from MIDI
QUERY_FIRMWARE = 0x79       # query the firmware name

# extended command set using sysex (0-127/0x00-0x7F)
# 0x00-0x0F reserved for user-defined commands */

SONAR_CONFIG = 0x62  # configure pins to control a Ping type sonar distance device
SONAR_DATA = 0x63  # distance data returned

SERVO_CONFIG = 0x70         # set max angle, minPulse, maxPulse, freq
STRING_DATA = 0x71          # a string message with 14-bits per char
SHIFT_DATA = 0x75           # a bitstream to/from a shift register
I2C_REQUEST = 0x76          # send an I2C read/write request
I2C_REPLY = 0x77            # a reply to an I2C read request
I2C_CONFIG = 0x78           # config I2C settings such as delay times and power pins
REPORT_FIRMWARE = 0x79      # report name and version of the firmware
SAMPLING_INTERVAL = 0x7A    # set the poll rate of the main loop
SYSEX_NON_REALTIME = 0x7E   # MIDI Reserved for non-realtime messages
SYSEX_REALTIME = 0x7F       # MIDI Reserved for realtime messages


# Pin modes.
# except from UNAVAILABLE taken from Firmata.h
UNAVAILABLE = -1
INPUT = 0          # as defined in wiring.h
OUTPUT = 1         # as defined in wiring.h
ANALOG = 2         # analog pin in analogInput mode
PWM = 3            # digital pin in PWM output mode
SERVO = 4          # digital pin in SERVO mode
SONAR = 0x0b       # Any pin in SONAR mode

# Pin types
DIGITAL = OUTPUT   # same as OUTPUT below
# ANALOG is already defined above

# Time to wait after initializing serial, used in Board.__init__
BOARD_SETUP_WAIT_TIME = 5

class PinAlreadyTakenError(Exception):
    pass

class InvalidPinDefError(Exception):
    pass

class NoInputWarning(RuntimeWarning):
    pass

class MarkRobot(object):
    """The Base class for any board."""
    firmata_version = None
    firmware = None
    firmware_version = None
    _command_handlers = {}
    _command = None
    _stored_data = []
    _parsing_sysex = False

    def __init__(self, sock):
        self.sock = sock
        self.setup_layout()


    def __del__(self):
        """
        The connection with the a board can get messed up when a script is
        closed without calling board.exit() (which closes the serial
        connection). Therefore also do it here and hope it helps.
        """
        self.exit()

    def send_as_two_bytes(self, val):
        self.sock.write(chr(val % 128) + chr(val >> 7))

    def setup_layout(self):
        """
        Setup the Pin instances based on the given board layout. Maybe it will
        be possible to do this automatically in the future, by polling the
        board for its type.
        """
        layout = {
        'digital' : tuple(x for x in range(14)),
        'analog' : tuple(x for x in range(6)),
        'pwm' : (3, 5, 6, 9, 10, 11),
        'use_ports' : True,
        'disabled' : (0, 1) # Rx, Tx, Crystal
        }

        # Create pin instances based on board layout
        self.analog = []
        for i in layout['analog']:
            self.analog.append(Pin(self, i))

        # Create pin instances for sonar
        self.sonar = []
        for i in range(20):
            self.sonar.append(Pin(self, i))

        self.digital = []
        self.digital_ports = []
        for i in xrange(0, len(layout['digital']), 8):
            num_pins = len(layout['digital'][i:i+8])
            port_number = i / 8
            self.digital_ports.append(Port(self, port_number, num_pins))

        # Allow to access the Pin instances directly
        for port in self.digital_ports:
            self.digital += port.pins

        # Setup PWM pins
        for i in layout['pwm']:
            self.digital[i].PWM_CAPABLE = True

        # Disable certain ports like Rx/Tx and crystal ports
        for i in layout['disabled']:
            self.digital[i].mode = UNAVAILABLE

        # Create a dictionary of 'taken' pins. Used by the get_pin method
        self.taken = { 'analog' : dict(map(lambda p: (p.pin_number, False), self.analog)),
                       'digital' : dict(map(lambda p: (p.pin_number, False), self.digital)) }

        # Setup default handlers for standard incoming commands
        self.add_cmd_handler(ANALOG_MESSAGE, self._handle_analog_message)
        self.add_cmd_handler(DIGITAL_MESSAGE, self._handle_digital_message)
        self.add_cmd_handler(REPORT_VERSION, self._handle_report_version)
        self.add_cmd_handler(REPORT_FIRMWARE, self._handle_report_firmware)
        self.add_cmd_handler(SONAR_DATA, self._handle_sonar_message)

    def add_cmd_handler(self, cmd, func):
        """Adds a command handler for a command."""
        len_args = len(inspect.getargspec(func)[0])
        def add_meta(f):
            def decorator(*args, **kwargs):
                f(*args, **kwargs)
            decorator.bytes_needed = len_args - 1 # exclude self
            decorator.__name__ = f.__name__
            return decorator
        func = add_meta(func)
        self._command_handlers[cmd] = func

    def get_pin(self, pin_def):
        """
        Returns the activated pin given by the pin definition.
        May raise an ``InvalidPinDefError`` or a ``PinAlreadyTakenError``.

        :arg pin_def: Pin definition as described below,
            but without the arduino name. So for example ``a:1:i``.

        'a' analog pin     Pin number   'i' for input 
        'd' digital pin    Pin number   'o' for output
                                        'p' for pwm (Pulse-width modulation)

        All seperated by ``:``. 
        """
        if type(pin_def) == list:
            bits = pin_def
        else:
            bits = pin_def.split(':')
        a_d = bits[0] == 'a' and 'analog' or 'digital'
        part = getattr(self, a_d)
        pin_nr = int(bits[1])
        if pin_nr >= len(part):
            raise InvalidPinDefError('Invalid pin definition: %s at position 3 on %s' % (pin_def, self.name))
        if getattr(part[pin_nr], 'mode', None)  == UNAVAILABLE:
            raise InvalidPinDefError('Invalid pin definition: UNAVAILABLE pin %s at position on %s' % (pin_def, self.name))
        if self.taken[a_d][pin_nr]:
            raise PinAlreadyTakenError('%s pin %s is already taken on %s' % (a_d, bits[1], self.name))
        # ok, should be available
        pin = part[pin_nr]
        self.taken[a_d][pin_nr] = True
        if pin.type is DIGITAL:
            if bits[2] == 'p':
                pin.mode = PWM
            elif bits[2] == 's':
                pin.mode = SERVO
            elif bits[2] is not 'o':
                pin.mode = INPUT
        else:
            pin.enable_reporting()
        return pin

    def pass_time(self, t):
        """Non-blocking time-out for ``t`` seconds."""
        cont = time.time() + t
        while time.time() < cont:
            time.sleep(0)

    def send_sysex(self, sysex_cmd, data=[]):
        """
        Sends a SysEx msg.

        :arg sysex_cmd: A sysex command byte
        :arg data: A list of 7-bit bytes of arbitrary data (bytes may be
            already converted to chr's)
        """
        self.sock.write(chr(START_SYSEX))
        self.sock.write(chr(sysex_cmd))
        for byte in data:
            try:
                byte = chr(byte)
            except TypeError:
                pass # byte is already a chr
            except ValueError:
                raise ValueError('Sysex data can be 7-bit bytes only. '
                    'Consider using utils.to_two_bytes for bigger bytes.')
            self.sock.write(byte)
        self.sock.write(chr(END_SYSEX))


    def iterate(self):
        """
        Reads and handles data from the microcontroller over the serial port.
        This method should be called in a main loop or in an :class:`Iterator`
        instance to keep this boards pin values up to date.
        """
        byte = self.sock.read()
        if not byte:
            return
        data = ord(byte)
        received_data = []
        handler = None
        if data < START_SYSEX:
            # These commands can have 'channel data' like a pin nummber appended.
            try:
                handler = self._command_handlers[data & 0xF0]
            except KeyError:
                return
            received_data.append(data & 0x0F)
            while len(received_data) < handler.bytes_needed:
                received_data.append(ord(self.sock.read()))
        elif data == START_SYSEX:
            data = ord(self.sock.read())
            handler = self._command_handlers.get(data)
            if not handler:
                return
            data = ord(self.sock.read())
            while data != END_SYSEX:
                received_data.append(data)
                data = ord(self.sock.read())
        else:
            try:
                handler = self._command_handlers[data]
            except KeyError:
                return
            while len(received_data) < handler.bytes_needed:
                received_data.append(ord(self.sock.read()))
        # Handle the data
        try:
            handler(*received_data)
        except ValueError:
            pass

    def get_firmata_version(self):
        """
        Returns a version tuple (major, minor) for the firmata firmware on the
        board.
        """
        return self.firmata_version

    def servo_config(self, pin, min_pulse=544, max_pulse=2400, angle=0):
        """
        Configure a pin as servo with min_pulse, max_pulse and first angle.
        ``min_pulse`` and ``max_pulse`` default to the arduino defaults.
        """
        if pin > len(self.digital) or self.digital[pin].mode == UNAVAILABLE:
            raise IOError("Pin %s is not a valid servo pin")
        data = itertools.chain([pin], to_two_bytes(min_pulse),
                                        to_two_bytes(max_pulse))
        self.send_sysex(SERVO_CONFIG, data)

        # set pin._mode to SERVO so that it sends analog messages
        # don't set pin.mode as that calls this method
        self.digital[pin]._mode = SERVO
        self.digital[pin].write(angle)

    def sonar_config(self, pin, cb=None, ping_interval=50, max_distance=200):
        """
        Configure a distance (sonar) sensor
        """
        if self.sonar[pin]._active == False:
            if max_distance > 200:
                max_distance = 200
            max_distance_lsb = max_distance & 0x7f
            max_distance_msb = (max_distance >> 7) & 0x7f
            data = [pin, pin, ping_interval, max_distance_lsb, max_distance_msb]

            self.sonar[pin]._mode = INPUT
            self.sonar[pin]._active = True

            self.send_sysex(SONAR_CONFIG, data)

    def exit(self):
        """Call this to exit cleanly."""
        # First detach all servo's, otherwise it somehow doesn't want to close...
        if hasattr(self, 'digital'):
            for pin in self.digital:
                if pin.mode == SERVO:
                    pin.mode = OUTPUT
        if hasattr(self, 'sp'):
            self.sock.close()

    # Command handlers
    def _handle_analog_message(self, pin_nr, lsb, msb):
        value = round(float((msb << 7) + lsb) / 1023, 4)
        # Only set the value if we are actually reporting
        try:
            if self.analog[pin_nr].reporting:
                self.analog[pin_nr].value = value
        except IndexError:
            raise ValueError

    def _handle_digital_message(self, port_nr, lsb, msb):
        """
        Digital messages always go by the whole port. This means we have a
        bitmask which we update the port.
        """
        mask = (msb << 7) + lsb
        try:
            self.digital_ports[port_nr]._update(mask)
        except IndexError:
            raise ValueError

    def _handle_sonar_message(self, pin_nr, lsb, msb):
        mask = (msb << 7) + lsb
        try:
            self.sonar[pin_nr].value = mask
        except IndexError:
            raise ValueError

    def _handle_report_version(self, major, minor):
        self.firmata_version = (major, minor)

    def _handle_report_firmware(self, *data):
        major = data[0]
        minor = data[1]
        self.firmware_version = (major, minor)
        self.firmware = two_byte_iter_to_str(data[2:])

    def system_reset(self):
        """
        Send the reset command to the Arduino.
        """
        data = chr(SYSTEM_RESET)
        self.sock.write(data)
        # reset all sonar status
        for p in self.sonar:
            p._active = False
        for p in self.analog:
            p.type = ANALOG
            p.mode = INPUT
            p.disable_reporting()
        for p in self.digital[2:]:
            p.type = DIGITAL
            p.mode = OUTPUT
            p.disable_reporting()

    def getFirmware(self):
        self.send_sysex(REPORT_FIRMWARE, [])

