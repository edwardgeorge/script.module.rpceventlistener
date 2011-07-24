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

    def schedule_event(self, event, time):
        heapq.heappush(self.schedule, (time, event))

    def schedule_event_in_secs(self, event, secs):
        self.schedule_event_in_secs(event, time.time() + secs)

    def _handle_scheduled_events(self):
        while self.schedule[0] < time.time():
            _, event = heapq.heappop(self.schedule)
            try:
                event()
            except Exception, e:
                pass  # TODO: log

    def _next_event_time(self):
        if self.schedule:
            return self.schedule[0]

    def _secs_to_next_event(self, cast_to_int=False):
        next_event = self._next_event_time()
        if not next_event:
            return
        secs = next_event - time.time()
        if cast_to_int:
            secs = int(secs)
        return max(0, secs)

    def run(self):
        try:
            finished = False
            while not finished:
                try:
                    for data in jsonstreamparser.read_from_socket(self.socket,
                            timeout=self._secs_to_next_event()):
                        self._handle_call(data)
                    finished = True
                except jsonstreamparser.Timeout, e:
                    self._handle_scheduled_events()
        except self.Quit, e:
            return
