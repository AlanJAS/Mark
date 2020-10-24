
try:
    import bluetooth
except:
    pass

from .mark import MarkRobot

class BlueSock(object):

    def __init__(self, host, name=None):
        self.host = host
        self.name = name
        self.sock = None
        self.type = 'bluetooth'

    def connect(self):
        self.sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
        self.sock.connect((self.host, 1))
        #self.sock.setblocking(1)
        self.sock.settimeout(1)
        return MarkRobot(self)

    def close(self):
        self.sock.close()
        self.sock = None

    def inWaiting(self):
        if self.sock:
            return True
        return False

    def write(self, data):
        self.sock.send(data)

    def read(self):
        return self.sock.recv(1)

def _check_mark(arg, value):
    return arg is None or arg == value

def find_blue_marks(host=None, name=None):
    ret = []
    try:
        for h, n in bluetooth.discover_devices(lookup_names=True):
            if _check_mark(host, h) and _check_mark(name, n):
                ret.append(BlueSock(h, n))
    except:
        pass
    return ret

