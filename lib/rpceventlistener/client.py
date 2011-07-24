import socket

import xbmc

from rpceventlistener import jsonstreamparser


def _get_errno(e):
    try:
        return e.errno
    except AttributeError, e:
        return e.args[0]


class RPCEventListener(object):
    class Quit(Exception):
        pass

    def __init__(self, delegate=None, addr=('127.0.0.1', 9090)):
        if delegate is None:
            self.delegate = self
        else:
            self.delegate = delegate
        self.socket = None
        while not self.socket and not xbmc.abortRequested:
            try:
                s = socket.socket()
                s.connect(addr)
                self.socket = s
            except socket.error, e:
                if _get_errno(e) == errno.ECONNREFUSED:
                    xbmc.sleep(1)
                else:
                    raise

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
        if method == 'System.OnQuit':
            raise self.Quit()

    def run(self):
        try:
            for data in jsonstreamparser.read_from_socket(self.socket):
                self._handle_call(data)
        except self.Quit, e:
            return
