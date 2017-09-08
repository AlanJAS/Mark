
import serial
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
        self.device = None

    def send(self, data):
        self.sock.write(data)

    def recv(self):
        return self.sock.read()
        

def find_serial_marks(host=None, name=None):
    ret = []
    status,output_usb = commands.getstatusoutput("ls /dev/ | grep ttyUSB")
    output_usb_parsed = output_usb.split('\n')
    status,output_acm = commands.getstatusoutput("ls /dev/ | grep ttyACM")
    output_acm_parsed = output_acm.split('\n')
    output = output_usb_parsed
    output.extend(output_acm_parsed)
    for dev in output:
        if not(dev == ''):
             ret.append(SerialSock('/dev/%s' % dev))
    return ret

