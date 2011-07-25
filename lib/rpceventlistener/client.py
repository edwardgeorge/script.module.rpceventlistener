import errno
import heapq
import socket
import time

try:
    import xbmc
except ImportError, e:
    # fake xbmc object for testing outside xbmc environment
    xbmc = type('xbmc', (object, ), {
        'abortRequested': False,
        'sleep': lambda self, s: time.sleep(s), })()

from rpceventlistener import jsonstreamparser

_TICK_PREFIX = 'tick_'


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

        self.schedule = []

        self.socket = None
        while not self.socket and not xbmc.abortRequested:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect(addr)
                self.socket = s
            except socket.error, e:
                if _get_errno(e) == errno.ECONNREFUSED:
                    xbmc.sleep(1)
                else:
                    raise
        if not self.socket:
            raise Exception()

    def _handle_call(self, data):
        method = data['method']
        method_name = 'handle_%s' % (method.replace('.', '_'), )
        m = getattr(self.delegate, method_name, None)
        if m is not None and callable(m):
            try:
                m(**data['params'])
            except Exception, e:
                pass
        if method == 'System.OnQuit':
            raise self.Quit()

    def schedule_event(self, event, time, *args, **kwargs):
        heapq.heappush(self.schedule, (time, event, args, kwargs))

    def schedule_event_in_secs(self, event, secs, *args, **kwargs):
        self.schedule_event(event, time.time() + secs, *args, **kwargs)

    def _handle_scheduled_events(self):
        while self.schedule and self.schedule[0][0] < time.time():
            _, event, args, kw = heapq.heappop(self.schedule)
            try:
                event(*args, **kw)
            except Exception, e:
                pass  # TODO: log

    def _next_event_time(self):
        if self.schedule:
            return self.schedule[0]

    def _secs_to_next_event(self, cast_to_int=False):
        next_event = self._next_event_time()
        if not next_event:
            return
        secs = next_event[0] - time.time()
        if cast_to_int:
            secs = int(secs)
        return max(0, secs)

    def _get_tick_callbacks(self):
        ret = []
        for i in dir(self.delegate):
            if i.startswith(_TICK_PREFIX):
                secs = i[len(_TICK_PREFIX):]
                attr = getattr(self.delegate, i)
                if callable(attr) and secs.isdigit():
                    ret.append((int(secs), attr))
        return ret

    def _process_tick(self, secs, callback):
        try:
            callback()
        except Exception, e:
            pass
        self.schedule_event_in_secs(self._process_tick, secs, secs, callback)

    def run(self):
        for secs, cb in self._get_tick_callbacks():
            self.schedule_event_in_secs(self._process_tick, secs, secs, cb)
        parser = jsonstreamparser.StreamParser(self.socket)
        while True:
            try:
                data = parser.next(timeout=self._secs_to_next_event())
                self._handle_call(data)
            except jsonstreamparser.Timeout, e:
                self._handle_scheduled_events()
            except (jsonstreamparser.ConnectionClosed, self.Quit), e:
                return
