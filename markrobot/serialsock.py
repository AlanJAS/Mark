
import serial

class SerialSock(object):

    def __init__(self, port):
        self.device = device
        self.type = 'serial'

    def __str__(self):
        return 'Serial (%s)' % (self.device.filename)

    def connect(self):
        self.sp = serial.Serial(port, baudrate)
        self.pass_time(BOARD_SETUP_WAIT_TIME)
        self.name = name
        if not self.name:
            self.name = port
        self.setup_layout(layout)
        # Iterate over the first messages to get firmware data
        while self.bytes_available():
            self.iterate()

    def close(self):
        self.device = None

    def send(self, data):
        self.device.write(OUT_ENDPOINT, data, TIMEOUT)

    def recv(self):
        data = self.device.read(IN_ENDPOINT, 64, TIMEOUT)
        return ''.join(chr(d & 0xFF) for d in data)

def find_marks(host=None, name=None):
    'Use to look for NXTs connected by USB only'
    for device in usb.core.find(find_all=True, idVendor=ID_VENDOR_LEGO, idProduct=ID_PRODUCT_NXT):
        yield USBSock(device)



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




