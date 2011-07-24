"""cheap and dirty json stream-parser."""
import select
import time

import simplejson
from simplejson.decoder import scanstring

_closemap = {']': '[', '}': '{'}


class Timeout(Exception):
    pass


def read_from_socket(s, timeout=None, bufsize=4096):
    p = FeedParser()
    if timeout is not None:
        timeout_time = time.time() + timeout
    while True:
        if timeout is not None:
            _timeout = timeout_time = time.time()
            if _timeout < 0:
                raise Timeout()
            r, w, e = select.select([s], [], [], timeout)
            if d not in r:
                raise Timeout()
        d = s.recv(bufsize)
        if not d:
            return
        while d:
            obj, d = p.feed(d) or ('', '')
            if obj:
                yield simplejson.loads(obj)


def stringparser(char):
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
            elif i in _closemap.values():
                self._stack.append([i])
            elif i in _closemap.keys():
                if self._stack and self._stack[-1][0] == _closemap[i]:
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
