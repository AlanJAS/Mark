#!/usr/bin/env python
# Copyright (c) 2017, Alan Aguiar <alanjas@hotmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import os
import sys
import commands

from gettext import gettext as _
from plugins.plugin import Plugin

from TurtleArt.tapalette import make_palette
from TurtleArt.tapalette import palette_name_to_index
from TurtleArt.tapalette import palette_blocks
from TurtleArt.tapalette import special_block_colors
from TurtleArt.talogo import logoerror
from TurtleArt.taconstants import CONSTANTS
from TurtleArt.taprimitive import Primitive, ArgSlot, ConstantArg
from TurtleArt.tatype import TYPE_INT, TYPE_FLOAT, TYPE_STRING, TYPE_NUMBER, TYPE_BOOL

sys.path.insert(0, os.path.abspath('./plugins/mark'))
import pyfirmata

VALUE = {_('HIGH'): 1, _('LOW'): 0}
MODE = {_('INPUT'): pyfirmata.INPUT, _('OUTPUT'): pyfirmata.OUTPUT,
        _('PWM'): pyfirmata.PWM, _('SERVO'): pyfirmata.SERVO,
        _('SONAR'): pyfirmata.SONAR}

ERROR = _('ERROR: Check the mark and the number of port')
ERROR_VALUE_A = _('ERROR: Value must be a number from 0 to 1')
ERROR_VALUE_S = _('ERROR: Value must be an integer from -100 to 180')
ERROR_SPEED = _('ERROR: The speed must be a number from 0 to 100')
ERROR_VALUE_D = _('ERROR: Value must be either HIGH or LOW, 0 or 1')
ERROR_MODE = _('ERROR: The mode must be either INPUT, OUTPUT, PWM or SERVO')
ERROR_VALUE_TYPE = _('ERROR: The value must be an integer')
ERROR_PIN_TYPE = _('ERROR: The pin must be an integer')
ERROR_PIN_CONFIGURED = _('ERROR: You must configure the mode for the pin')

COLOR_NOTPRESENT = ["#A0A0A0","#808080"]
COLOR_PRESENT = ["#FF0000", "#A06060"]


class Mark(Plugin):

    def __init__(self, parent):
        Plugin.__init__(self)
        self.tw = parent
        self._baud = 57600
        self.active_mark = 0
        self._marks = []
        self._marks_it = []

    def setup(self):
        """ Setup is called once, when the Turtle Window is created. """

        palette = make_palette('mark', COLOR_NOTPRESENT,
                             _('Palette of mark robot'),
                             translation=_('mark'))

        palette.add_block('markrefresh',
                     style='basic-style',
                     label=_('refresh mark'),
                     prim_name='markrefresh',
                     help_string=_('Search for connected marks.'))
        self.tw.lc.def_prim('markrefresh', 0,
            Primitive(self.refresh))
        special_block_colors['markrefresh'] = COLOR_PRESENT[:]

        palette.add_block('markselect',
                          style='basic-style-1arg',
                          default = 1,
                          label=_('mark'),
                          help_string=_('set current mark board'),
                          prim_name = 'markselect')
        self.tw.lc.def_prim('markselect', 1,
            Primitive(self.select, arg_descs=[ArgSlot(TYPE_NUMBER)]))

        palette.add_block('markcount',
                          style='box-style',
                          label=_('number of marks'),
                          help_string=_('number of mark boards'),
                          prim_name = 'markcount')
        self.tw.lc.def_prim('markcount', 0,
            Primitive(self.count, TYPE_INT))

        palette.add_block('markname',
                  style='number-style-1arg',
                  label=_('mark name'),
                  default=[1],
                  help_string=_('Get the name of an mark'),
                  prim_name='markname')
        self.tw.lc.def_prim('markname', 1,
            Primitive(self.getName, TYPE_STRING, [ArgSlot(TYPE_NUMBER)]))

        palette.add_block('markfirmware',
                  style='number-style-1arg',
                  label=_('mark firmware'),
                  default=[1],
                  help_string=_('Get the version of an mark firmware'),
                  prim_name='markfirmware')
        self.tw.lc.def_prim('markfirmware', 1,
            Primitive(self.getFirmware, TYPE_STRING, [ArgSlot(TYPE_NUMBER)]))

        # motors

        palette.add_block('markTurnMotorA',
                  style='basic-style-1arg',
                  label=_('mark motor A'),
                  default=100,
                  help_string=_('Turn motor A'),
                  prim_name='markTurnMotorA')
        self.tw.lc.def_prim('markTurnMotorA', 1,
            Primitive(self.markTurnMotorA, arg_descs=[ArgSlot(TYPE_INT)]))
 
        palette.add_block('markTurnMotorB',
                  style='basic-style-1arg',
                  label=_('mark motor B'),
                  default=100,
                  help_string=_('Turn motor B'),
                  prim_name='markTurnMotorB')
        self.tw.lc.def_prim('markTurnMotorB', 1,
            Primitive(self.markTurnMotorB, arg_descs=[ArgSlot(TYPE_INT)]))

        palette.add_block('markBrakeMotorA',
                  style='basic-style',
                  label=_('brake motor A'),
                  help_string=_('Brake motor A'),
                  prim_name='markBrakeMotorA')
        self.tw.lc.def_prim('markBrakeMotorA', 0,
            Primitive(self.markBrakeMotorA))

        palette.add_block('markBrakeMotorB',
                  style='basic-style',
                  label=_('brake motor B'),
                  help_string=_('Brake motor B'),
                  prim_name='markBrakeMotorB')
        self.tw.lc.def_prim('markBrakeMotorB', 0,
            Primitive(self.markBrakeMotorB))

        palette.add_block('markServo',
                  style='basic-style-2arg',
                  label=[_('mark servo'), _('pin'), _('angle')],
                  default=[10, 100],
                  help_string=_('put a mark servo in angle'),
                  prim_name='markServo')
        self.tw.lc.def_prim('markServo', 2,
            Primitive(self.markServo, arg_descs=[ArgSlot(TYPE_NUMBER), ArgSlot(TYPE_NUMBER)]))

        # sensors

        palette.add_block('markGray',
                  style='number-style-1arg',
                  label=[_('mark gray')],
                  default=[0],
                  help_string=_('Read gray value from specific port. Value may be between 0 and 100'),
                  prim_name='markGray')
        self.tw.lc.def_prim('markGray', 1,
            Primitive(self.markGray, TYPE_NUMBER, arg_descs=[ArgSlot(TYPE_NUMBER)]))

        palette.add_block('markDist',
                  style='number-style-1arg',
                  label=[_('mark dist')],
                  default=[0],
                  help_string=_('Read distance value from specific port. Value may be between 0 and 100'),
                  prim_name='markDist')
        self.tw.lc.def_prim('markDist', 1,
            Primitive(self.markDist, TYPE_NUMBER, arg_descs=[ArgSlot(TYPE_NUMBER)]))

        palette.add_block('markButton',
                  style='boolean-1arg-block-style',
                  label=[_('mark button')],
                  default=[1],
                  help_string=_('Read the button state. When is 1 is pressed, 0 otherwise'),
                  prim_name='markButton')
        self.tw.lc.def_prim('markButton', 1,
            Primitive(self.markButton, TYPE_BOOL, arg_descs=[ArgSlot(TYPE_NUMBER)]))

        palette.add_block('markLED',
                          style='basic-style-2arg',
                          default = [1, 1],
                          label=[_('mark LED'), _('pin'), _('on/off')],
                          help_string=_('turn on/off LED'),
                          prim_name = 'markLED')
        self.tw.lc.def_prim('markLED', 2,
            Primitive(self.markLED, arg_descs=[ArgSlot(TYPE_NUMBER), ArgSlot(TYPE_NUMBER)]))




    ############################### Turtle signals ############################

    def quit(self):
        for dev in self._marks:
            try:
                dev.exit()
            except:
                pass

    def stop(self):
        self.markTurnMotorA(0)
        self.markTurnMotorB(0)
        self.resetBoards()

    ###########################################################################

    def _check_init(self):
        n = len(self._marks)
        if (self.active_mark > n) or (self.active_mark < 0):
            raise logoerror(_('Not found mark %s') % (self.active_mark + 1))

    def resetBoards(self):
        for m in self._marks:
            try:
                m.system_reset()
            except:
                pass

    def markTurnMotorA(self, power):
        self._turn_motor(11, 13, power)

    def markTurnMotorB(self, power):
        self._turn_motor(5, 12, power)

    def markBrakeMotorA(self):
        self._turn_motor(11, 13, 0)
        
    def markBrakeMotorB(self):
        self._turn_motor(5, 12, 0)

    def markServo(self, pin, angle):
        self._turn_servo(pin, angle)

    def markGray(self, pin):
        try:
            pin = int(pin)
        except:
            raise logoerror(ERROR_PIN_TYPE)
        res = -1
        try:
            res = self.analogRead(pin)
        except:
            pass
        if not(res == -1):
            return int(res * 100)
        return res

    def _convert_pin(self, pin):
        """
        Convert analog pin to digital equivalent
        """
        if pin < 6:
            return pin + 14
        else:
            return pin

    def markDist(self, pin):
        try:
            pin = int(pin)
        except:
            raise logoerror(ERROR_PIN_TYPE)
        res = -1
        try:
            a = self._marks[self.active_mark]
            digital_pin = self._convert_pin(pin)

            a.sonar_config(digital_pin)
            
            a.sonar[digital_pin].enable_reporting()
            a.pass_time(0.05)
            res = a.sonar[digital_pin].read()
            a.sonar[pin].disable_reporting()
        except:
            pass
        if not(res == False):
            return res
        return -1

    def markButton(self, pin):
        res = -1
        try:
            res = self.analogRead(pin)
        except:
            pass
        if not(res == -1):
            if res > 0:
                return 0
            else:
                return 1
        return res

    def markLED(self, pin, on_off):
        try:
            pin = int(pin)
        except:
            raise logoerror(ERROR_PIN_TYPE)
        try:
            a = self._marks[self.active_mark]
            new_mode = MODE[_('OUTPUT')]
            a.digital[pin]._set_mode(new_mode)
            a.digital[pin].write(on_off)
        except:
            pass

    def _turn_motor(self, pin_p, pin_s, power):
        try:
            power = float(power)
        except:
            raise logoerror(ERROR_VALUE_TYPE)
        if (power < -100) or (power > 100):
            raise logoerror(ERROR_SPEED)
        if power < 0:
            sense = 1
            power = -1 * power
        else:
            sense = 0
        power = power / 100.0
        try:
            a = self._marks[self.active_mark]
            # check mode pwm and set the power
            actual_mode = a.digital[pin_p]._get_mode()
            new_mode = MODE[_('PWM')]
            if actual_mode <> new_mode:
                a.digital[pin_p]._set_mode(new_mode)
            a.digital[pin_p].write(power)
            # check mode output and set the sense
            actual_mode = a.digital[pin_s]._get_mode()
            new_mode = MODE[_('OUTPUT')]
            if actual_mode <> new_mode:
                a.digital[pin_s]._set_mode(new_mode)
            a.digital[pin_s].write(sense)
        except:
            raise logoerror(ERROR)

    def _turn_servo(self, pin, angle):
        try:
            pin = int(pin)
        except:
            raise logoerror(ERROR_PIN_TYPE)
        try:
            angle = int(angle)
        except:
            raise logoerror(ERROR_VALUE_S)
        if (angle < 0) or (angle > 180):
            raise logoerror(ERROR_VALUE_S)
        try:
            a = self._marks[self.active_mark]
            actual_mode = a.digital[pin]._get_mode()
            new_mode = MODE[_('SERVO')]
            if actual_mode <> new_mode:
                a.digital[pin]._set_mode(new_mode)
            a.digital[pin].write(angle)
        except:
            raise logoerror(ERROR)

        

    def pinMode(self, pin, mode):
        self._check_init()
        try:
            pin = int(pin)
        except:
            raise logoerror(ERROR_PIN_TYPE)
        if (mode in MODE):
            try:
                a = self._marks[self.active_mark]
                actual_mode = a.digital[pin]._get_mode()
                new_mode = MODE[mode]
                if actual_mode <> new_mode:
                    a.digital[pin]._set_mode(new_mode)
            except:
                raise logoerror(ERROR)
        else:
            raise logoerror(ERROR_MODE)

    def analogWrite(self, pin, value):
        self._check_init()
        try:
            pin = int(pin)
        except:
            raise logoerror(ERROR_PIN_TYPE)
        try:
            tmp = float(value)
        except:
            raise logoerror(ERROR_VALUE_TYPE)
        try:
            a = self._marks[self.active_mark]
            mode = a.digital[pin]._get_mode()
        except:
            raise logoerror(ERROR)
        if mode == MODE[_('PWM')]:
            min_value = 0
            max_value = 100
            error = ERROR_VALUE_A
        elif mode == MODE[_('SERVO')]:
            min_value = 0
            max_value = 180
            error = ERROR_VALUE_S
        else:
            raise logoerror(ERROR_PIN_CONFIGURED)
        if not((tmp < min_value) or (tmp > max_value)):
            try:
                a = self._marks[self.active_mark]
                a.digital[pin].write(tmp)
            except:
                raise logoerror(ERROR)
        else:
            raise logoerror(error)

    def digitalWrite(self, pin, value):
        self._check_init()
        try:
            pin = int(pin)
        except:
            raise logoerror(ERROR_PIN_TYPE)
        try:
            value = int(value)
        except:
            raise logoerror(ERROR_VALUE_TYPE)
        try:
            a = self._marks[self.active_mark]
            mode = a.digital[pin]._get_mode()
        except:
            raise logoerror(ERROR)
        print a, mode
        if mode != MODE[_('OUTPUT')]:
            raise logoerror(ERROR_PIN_CONFIGURED)
        if (value < 0) or (value > 1):
            raise logoerror(ERROR_VALUE_D)
        else:
            try:
                a = self._marks[self.active_mark]
                a.digital[pin].write(value)
            except:
                raise logoerror(ERROR)

    def analogRead(self, pin):
        #self._check_init()
        try:
            pin = int(pin)
        except:
            raise logoerror(ERROR_PIN_TYPE)
        res = -1
        try:
            a = self._marks[self.active_mark]
            a.analog[pin].enable_reporting()
            a.pass_time(0.05) # wait for the iterator to start receiving data
            res = a.analog[pin].read()
            a.analog[pin].disable_reporting()
        except:
            pass
        return res

    def digitalRead(self, pin):
        self._check_init()
        try:
            pin = int(pin)
        except:
            raise logoerror(ERROR_PIN_TYPE)
        try:
            a = self._marks[self.active_mark]
            mode = a.digital[pin]._get_mode()
        except:
            raise logoerror(ERROR)
        if mode != MODE[_('INPUT')]:
            raise logoerror(ERROR_PIN_CONFIGURED)
        res = -1
        try:
            a = self._marks[self.active_mark]
            a.digital[pin].enable_reporting()
            a.pass_time(0.05) # wait for the iterator to start receiving data
            if a.digital[pin].read() is None:
                # if the library returns None it is actually False  not being updated
                res = False
            else:
                res = a.digital[pin].read()
            a.digital[pin].disable_reporting()
        except:
            pass
        return res

    def select(self, i):
        n = len(self._marks)
        try:
            i = int(i)
        except:
            raise logoerror(_('The device must be an integer'))
        i = i - 1
        if (i < n) and (i >= 0):
            self.active_mark = i
        else:
            raise logoerror(_('Not found mark %s') % (i + 1))

    def count(self):
        return len(self._marks)

    def getName(self, i):
        n = len(self._marks)
        try:
            i = int(i)
        except:
            raise logoerror(_('The device must be an integer'))
        i = i - 1
        if (i < n) and (i >= 0):
            a = self._marks[i]
            return a.name
        else:
            raise logoerror(_('Not found mark %s') % (i + 1))

    def getFirmware(self, i):
        try:
            a = self._marks[self.active_mark]
            a.getFirmware()
            return a.firmware_version
        except:
            return "(0, 0)"

    def change_color_blocks(self):
        if len(self._marks) > 0:
            mark_present = True
        else:
            mark_present = False
        index = palette_name_to_index('mark')
        if index is not None:
            mark_blocks = palette_blocks[index]
            for block in self.tw.block_list.list:
                if block.type in ['proto', 'block']:
                    if block.name in mark_blocks:
                        if (mark_present) or (block.name == 'markrefresh'):
                            special_block_colors[block.name] = COLOR_PRESENT[:]
                        else:
                            special_block_colors[block.name] = COLOR_NOTPRESENT[:]
                        block.refresh()
            self.tw.regenerate_palette(index)

    def refresh(self):
        #Close actual marks
        for dev in self._marks:
            try:
                dev.exit()
            except:
                pass
        self._marks = []
        self._marks_it = []
        #Search for new marks
        status,output_usb = commands.getstatusoutput("ls /dev/ | grep ttyUSB")
        output_usb_parsed = output_usb.split('\n')
        status,output_acm = commands.getstatusoutput("ls /dev/ | grep ttyACM")
        output_acm_parsed = output_acm.split('\n')
        output = output_usb_parsed
        output.extend(output_acm_parsed)
        for dev in output:
            if not(dev == ''):
                n = '/dev/%s' % dev
                try:
                    board = pyfirmata.Arduino(n, baudrate=self._baud)
                    it = pyfirmata.util.Iterator(board)
                    it.start()
                    self._marks.append(board)
                    self._marks_it.append(it)
                except Exception, err:
                    print err
                    raise logoerror(_('Error loading %s board') % n)
        self.change_color_blocks()

