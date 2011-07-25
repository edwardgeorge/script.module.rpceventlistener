from rpceventlistener import RPCEventListener
import simplejson
import time
import xbmc


def log(msg, level=xbmc.LOGNOTICE):
    xbmc.log(msg="rpceventlistener example: %s" % (msg, ),
        level=level)


class MyListener(RPCEventListener):
    def handle_Player_OnPlay(self, data, sender):
        if sender != 'xbmc':
            return
        if data.get('type') == 'movie' and 'id' in data:
            fields = ['title', 'year', 'imdbnumber', ]
            d = simplejson.dumps({
                'jsonrpc': '2.0',
                'method': 'VideoLibrary.GetMovieDetails',
                'params': {'movieid': data['id'],
                           'fields': fields, },
                'id': 1, })
            r = xbmc.executeJSONRPC(d)
            log("moviedetails: %r" % r)

            # demo scheduling a task...
            self.schedule_event_in_secs(log, 2,
                "I happen 2 seconds later!")

    def tick_60(self):
        # I get called every 60 seconds
        log("TICK!")


log("service run!")
listener = MyListener()
log("listener connected")
listener.run()
log("quit!")
