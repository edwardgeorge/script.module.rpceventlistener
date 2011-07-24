import socket

from rpceventlistener import jsonstreamparser


class RPCClient(object):
    class Quit(exception):
        pass

    def __init__(self, delegate=None):
        if delegate is None:
            self.delegate = self
        else:
            self.delegate = delegate
        s = socket.socket()
        s.connect(addr)
        self.socket = s

    def _handle_call(self, data):
        method = data['method']
        method_name = 'handle_%s' % (method.replace('.', '_'), )
        try:
            m = getattr(self.delegate, method_name)
        except AttributeError, e:
            return
        try:
            m(**data['params'])
        except Exception, e:
            pass

    def run(self):
        try:
            for data in jsonstreamparser.read_from_socket(self.socket):
                self._handle_call(data)
        except self.Quit, e:
            return
