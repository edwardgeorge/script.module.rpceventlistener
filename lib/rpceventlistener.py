import socket

import simplejson
from simplejson import JSONDecodeError

def stringparser(char):
    from simplejson.decoder import scanstring
    data = [char]
    def feed(s):
        data.append(s)
        d = ''.join(data)
        try:
            string, i = scanstring(d, 1)
            return True, d[:i], d[i:]
        except simplejson.JSONDecodeError, e:
            return False, d, ''
    return feed


closemap = {']': '[', '}': '{'}


class FeedParser(object):
    def __init__(self):
        self._stack = []
        self._string_state = None

    def feed(self, s):
        while s:
            if self._string_state:
                a, b, s = self._string_state(s)
                if a:
                    self._string_state = None
                    if self._stack:
                        self._stack[-1].append(b)
                    else:
                        return b, s

            i, s = s[0], s[1:]
            if i == '"':
                self._string_state = stringparser(i)
            elif i in closemap.values():
                self._stack.append([i])
            elif i in closemap.keys():
                if self._stack and self._stack[-1][0] == closemap[i]:
                    k = self._stack.pop()
                else:
                    raise ValueError()
                k.append(i)
                d = ''.join(k)
                if self._stack:
                    self._stack[-1].append(d)
                else:
                    return d, s
            elif self._stack:
                self._stack[-1].append(i)
            else:
                raise ValueError()


def read_from_socket(s, bufsize=4096):
    p = FeedParser()
    while True:
        d = s.recv(bufsize)
        if not d:
            return
        while d:
            obj, d = p.feed(d) or ('', '')
            if obj:
                yield simplejson.loads(obj)


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
            for data in read_from_socket(self.socket):
                self._handle_call(data)
        except self.Quit, e:
            return
