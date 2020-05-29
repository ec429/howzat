#!/usr/bin/python3
import json
import select
import socket
import sys

import coroutine
import howzat

Value = coroutine.Value

SERVER_VERSION = [1, 0, 0]
DEFAULT_MOTD = "Welcome to the Howzat server."

class WaitForAction(coroutine.WaitingFor):
    def __init__(self, player, *actions):
        def match(**d):
            return d.get('type') == 'action' and d.get('action' in actions)
        super(WaitForAction, self).__init__(player, match)

class RemotePlayer(howzat.Player):
    def __init__(self, name, client):
        self.client = client
        super(RemotePlayer, self).__init__(name)
    def wait_for_action(self, *actions):
        return WaitForAction(self, *actions)
    def randint(self, a, b, prompt=None):
        # Should never be called, we've overridden all the methods that call it
        raise NotImplementedError()
    def flip_coin(self, prompt=None):
        # Wait for client to trigger
        while True:
            self.client.action('flip coin', reason=prompt if prompt else "Flip coin")
            if (yield self.wait_for_action('flip coin')) is not None:
                break
        # Two-part millisecond wheel
        t = time.time() % 0.001
        r = bool(int((t * 2000.0) % 2))
        print("%s flipped %s" % (self.name, "tails" if r else "heads"))
        yield Value(r)
    def roll_d6(self, prompt=None):
        # Wait for client to trigger
        while True:
            self.client.action('roll', dice=1, reason=prompt if prompt else "Roll")
            if (yield self.wait_for_action('roll')) is not None:
                break
        # Six-part millisecond wheel
        t = time.time() % 0.001
        r = (int(t * 6000.0) % 6) + 1
        print("%s rolled d6 %s" % (self.name, chr(0x267f + r)))
        yield Value(r)
    def roll_2d6(self, prompt=None):
        # Wait for client to trigger
        while True:
            self.client.action('roll', dice=2, reason=prompt if prompt else "Roll")
            if (yield self.wait_for_action('roll')) is not None:
                break
        # Thirty-six-part millisecond wheel
        t = time.time() % 0.001
        a = (int(t * 6000.0) % 6) + 1
        b = (int(t * 36000.0) % 6) + 1
        r = a + b
        print("%s rolled 2d6 %s%s -> %d" % (self.name, chr(0x267f + a), chr(0x267f + b), r))
        yield Value(r)
    def call_toss(self):
        while True:
            self.client.action('call toss')
            d = yield self.wait_for_action('call toss')
            if d is None: # reconnected
                continue
            if isinstance(d.get('tails'), bool):
                yield Value(d['tails'])
            self.client.error("'call toss' requires 'tails': bool")
    def choose_to_bat(self):
        while True:
            self.client.action('choose first')
            d = yield self.wait_for_action('choose first')
            if d is None: # reconnected
                continue
            if isinstance(d.get('bat'), bool):
                yield Value(d['bat'])
            self.client.error("'choose first' requires 'bat': bool")
    def maybe_choose_bowler(self, inns):
        curr = inns.bowling
        legal = inns.legal_bowlers()
        legal_names = dict((p.name, p) for p in legal)
        keeper_names = dict((p.name, p) for p in inns.fteam.field)
        while True:
            self.client.action('choose bowler', legal=legal_names.keys(), current=curr.name)
            d = yield self.wait_for_action('choose bowler', 'choose keeper')
            if d is None: # reconnected
                continue
            if d['action'] == 'choose keeper':
                if d.get('keeper') in keeper_names:
                    inns.choose_keeper(keeper_names[d['keeper']])
                else:
                    self.client.error("'choose keeper' requires a 'keeper' from player list")
                continue
            if d.get('bowler') in legal_names:
                p = legal_names[d['bowler']]
                if p.keeper:
                    self.client.error("'choose bowler': 'bowler': %s is currently keeping wicket (try 'choose keeper' to change)" % p.name)
                    continue
                yield Value(p)
            self.client.error("'choose bowler' requires a 'bowler' from legal list")
    def choose_keeper(self, legal):
        legal_names = dict((p.name, p) for p in legal)
        while True:
            self.client.action('choose keeper', legal=legal_names.keys())
            d = yield self.wait_for_action('choose keeper')
            if d is None: # reconnected
                continue
            if d.get('keeper') in legal_names:
                yield Value(legal_names[d['keeper']])
            self.client.error("'choose keeper' requires a 'keeper' from legal list")
    def choose_batsman(self, legal):
        legal_names = dict((p.name, p) for p in legal)
        while True:
            self.client.action('next bat', legal=legal_names.keys())
            d = yield self.wait_for_action('next bat')
            if d is None: # reconnected
                continue
            if d.get('batsman') in legal_names:
                yield Value(legal_names[d['batsman']])
            self.client.error("'next bat' requires a 'batsman' from legal list")

class SocketClosed(Exception): pass

class Client(object):
    def __init__(self, sock, server, debug=False):
        self.sock = sock
        self.server = server
        self.dbg = debug
        self.rxbuf = b''
        self.txbuf = b''
        self.registered = False
        self.name = sock.fileno()
        self.send('welcome', version=SERVER_VERSION, message=self.server.motd)
    def debug(self, cls, *args):
        if self.dbg:
            print('DBG %s %s' % (cls, ' '.join(map(str, args))))
    def debug_rx(self, *args):
        self.debug('rx', *args)
    def debug_tx(self, *args):
        self.debug('tx', *args)
    def maybe_read_msg(self):
        data = self.sock.recv(256)
        if not len(data):
            raise SocketClosed('End-of-file condition on socket')
        self.rxbuf += data
    def rx(self):
        if b'\n' not in self.rxbuf:
            return None
        msg, _, self.rxbuf = self.rxbuf.partition(b'\n')
        try:
            d = json.loads(msg.decode('utf8'))
            self.debug_rx(d)
            return d
        except Exception as e:
            self.send('error', message="Malformed message: %r" % e)
            return None
    def write_all_msg(self):
        try:
            while self.txbuf:
                self.maybe_write_msg()
        except:
            self.txbuf = b''
    def maybe_write_msg(self):
        if not self.txbuf:
            return
        b = self.sock.send(self.txbuf)
        self.txbuf = self.txbuf[b:]
    def send(self, typ, **d):
        msg = {'type': typ}
        msg.update(d)
        self.tx(msg)
    def tx(self, d):
        self.debug_tx(d)
        j = json.dumps(d) + '\n'
        self.txbuf += j.encode('utf8')

class Server(object):
    def __init__(self, port=0x6666, motd=DEFAULT_MOTD, debug=0):
        self.sock = socket.socket()
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(('localhost', port))
        self.sock.listen(5)
        self.motd = motd
        self.dbg = debug
        self.clients = {}
    def debug(self, *args):
        if self.dbg:
            print(' '.join(map(str, args)))
    def try_shutdown(self, sock):
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
    def handle(self, client, msg):
        typ = msg.get('type')
        if typ == 'hello':
            if client.registered:
                return client.send('error', message='Already registered')
            username = msg.get('username')
            if not isinstance(username, str):
                return client.send('error', message="Bad 'username' in 'hello'")
            self.debug('Renamed', client.name, 'to', username)
            # Client rename means its key in self.clients changes
            del self.clients[client.name]
            client.name = username
            self.clients[client.name] = client
            return
        if typ == 'goodbye':
            self.debug('Goodbye', client.name)
            self.try_shutdown(client.sock)
            client.sock = None
            del self.clients[client.name]
            return
        client.send('error', message="Unhandled message 'type': %r" % (typ,))
        raise Exception("Unhandled message from", client.name, msg)
    def halt(self):
        self.debug('Shutting down')
        self.sock.close()
        for c in self.clients.values():
            self.debug('Closing', c.name)
            c.send('error', message='Server halted by operator')
            c.write_all_msg()
            self.try_shutdown(c.sock)
        self.debug('Shutdown complete')
    def tick(self, timeout=1.0):
        cfds = tuple(client.sock.fileno() for client in self.clients.values())
        r, w, x = select.select((sys.stdin.fileno(), self.sock.fileno()) + cfds, cfds, (), timeout)
        if sys.stdin.fileno() in r:
            inp = sys.stdin.readline().rstrip('\n')
            if inp.startswith('/halt'):
                return True
        if self.sock.fileno() in r:
            ns, _ = self.sock.accept()
            c = Client(ns, self, debug=self.dbg>1)
            self.debug('Accepted a new connection', c.name)
            self.clients[c.name] = c
        for c in list(self.clients.values()):
            fd = c.sock.fileno()
            if fd in r:
                try:
                    c.maybe_read_msg()
                except SocketClosed:
                    self.debug('Connection closed by', c.name)
                    del self.clients[c.name]
                except Exception as e:
                    self.debug('Lost connection to', c.name)
                    self.try_shutdown(c.sock)
                    del self.clients[c.name]
                else:
                    while True:
                        msg = c.rx()
                        if msg is None:
                            break
                        try:
                            self.handle(c, msg)
                        except Exception as e:
                            print(e)
            if c.sock is None:
                continue
            if fd in w:
                try:
                    c.maybe_write_msg()
                except Exception as e:
                    self.debug('Lost connection to', c.name)
                    self.try_shutdown(c.sock)
                    del self.clients[c.name]

s = Server(debug=True)
while True:
    if s.tick():
        break
s.halt()
