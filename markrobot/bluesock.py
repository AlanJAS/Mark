
try:
    import bluetooth
except:
    pass

from mark import MarkRobot

class BlueSock(object):

    def __init__(self, host):
        self.host = host
        self.sock = None
        self.type = 'bluetooth'

    def connect(self):
        sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
        sock.connect((self.host, 1))
        self.sock = sock
        # no bloqueo
        #self.sock.setblocking(1)
        self.sock.settimeout(1)
        return MarkRobot(self)

    def close(self):
        self.sock.close()

    def send(self, data):
        self.sock.send(data)

    def recv(self):
        return self.sock.recv(1)

def _check_markk(arg, value):
    return arg is None or arg == value

def find_blue_bricks(host=None, name=None):
    ret = []
    try:
        for h, n in bluetooth.discover_devices(lookup_names=True):
            if _check_mark(host, h) and _check_mark(name, n):
                ret.append(BlueSock(h))
    except:
        pass
    return ret

