
import serial
import subprocess
from mark import MarkRobot

class SerialSock(object):

    def __init__(self, port):
        self.port = port
        self.name = port
        self.sock = None
        self.type = 'serial'

    def connect(self):
        self.sock = serial.Serial(self.port, 115200)
        return MarkRobot(self)

    def close(self):
        self.sock.close()
        self.sock = None

    def inWaiting(self):
        if self.sock:
            return self.sock.inWaiting()
        return False

    def write(self, data):
        self.sock.write(data)

    def read(self):
        return self.sock.read()
        

def find_serial_marks(host=None, name=None):
    ret = []
    output_usb_parsed = []
    output_acm_parsed = []
    try:
        output_usb = subprocess.check_output('ls /dev/ | grep ttyUSB', shell=True)
        output_usb = output_usb.decode()
        output_usb_parsed = output_usb.split('\n')
    except:
        pass
    try:
        output_acm = subprocess.check_output('ls /dev/ | grep ttyACM', shell=True)
        output_acm = output_acm.decode()
        output_acm_parsed = output_acm.split('\n')
    except:
        pass
    output = output_usb_parsed
    output.extend(output_acm_parsed)
    for dev in output:
        if not(dev == ''):
             ret.append(SerialSock('/dev/%s' % dev))
    return ret

