#!/usr/bin/python3
import argparse
import getpass
import json
import select
import shlex
import socket
import sys

class Croaked(Exception): pass
class SocketClosed(Exception): pass

class Connection(object):
    def __init__(self, host='localhost', port=0x6666, username=getpass.getuser(), playername=None):
        self.buf = b''
        self.sock = socket.socket()
        try:
            self.sock.connect((host, port))
        except Exception as e:
            self.sock = None
            raise
        self.username = username
        self.playername = playername
        self.register()
        self.room = set()
    def debug(self, cls, *args):
        pass
    def debug_rx(self, *args):
        self.debug('rx', *args)
    def debug_tx(self, *args):
        self.debug('tx', *args)
    def try_shutdown(self):
        if self.sock is None:
            return
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
    def read_msg(self):
        while b'\n' not in self.buf:
            self.buf += self.sock.recv(256)
        msg, _, self.buf = self.buf.partition(b'\n')
        d = json.loads(msg.decode('utf8'))
        self.debug_rx(d)
        return d
    def maybe_read_msg(self, timeout=0.1):
        if b'\n' not in self.buf:
            r, w, x = select.select((self.sock.fileno(),), (), (), timeout)
            if self.sock.fileno() in r:
                data = self.sock.recv(256)
                if not len(data):
                    self.sock.close()
                    self.sock = None
                    raise SocketClosed('End-of-file condition on socket')
                self.buf += data
        if b'\n' not in self.buf:
            return None
        msg, _, self.buf = self.buf.partition(b'\n')
        d = json.loads(msg.decode('utf8'))
        self.debug_rx(d)
        return d
    def write_msg(self, d):
        self.debug_tx(d)
        j = json.dumps(d) + '\n'
        while j:
            b = self.sock.send(j.encode('utf8'))
            j = j[b:]
    def croak(self, msg, swallow=False):
        try:
            self.write_msg({'type': 'error', 'error': str(msg)})
        except Exception as e:
            print("Failed to croak %r: %s" % (msg, e))
        self.try_shutdown()
        self.sock = None
        if not swallow:
            raise Croaked(msg)
    def register(self):
        welcome = self.read_msg()
        if welcome.get('type') != 'welcome':
            self.croak("Expected welcome message, got %s" % (welcome.get('type'),))
        version = welcome.get('version')
        if not isinstance(version, list):
            self.croak("Malformed welcome message (version: %r)" % (version,))
        if version[0] != 1:
            self.croak("This client only supports protocol version 1 (not %r)" % (version[0],))
        self.server_version = version
        self.motd = welcome.get('message')
        hello = {'type': 'hello', 'username': self.username}
        if self.playername is not None:
            hello['player'] = self.playername
        self.write_msg(hello)
    def __del__(self):
        self.goodbye("Client connection GCed")
    def goodbye(self, msg=None):
        if self.sock is None:
            return
        gb = {'type': 'goodbye'}
        if msg is not None:
            gb['message'] = msg
        self.write_msg(gb)
        self.try_shutdown()
        self.sock = None
    def maybe_read_and_handle(self, timeout=0.1):
        msg = self.maybe_read_msg(timeout=timeout)
        if msg is None:
            return
        if 'type' not in msg:
            self.croak("Message without type: %s" % json.dumps(msg))
        typ = msg.pop('type')
        if isinstance(typ, str):
            method = 'handle_'+typ
            if hasattr(self, method):
                try:
                    return getattr(self, method)(**msg)
                except Croaked:
                    raise
                except Exception as e:
                    self.croak("Failed to handle message %s: %r" % (json.dumps(msg), e))
        self.croak("Unhandled message type: %s %s" % (typ, json.dumps(msg)))
    def handle_enter(self, user):
        if user == self.username:
            self.room = set()
        else:
            self.room.add(user)
    def handle_exit(self, user):
        if user == self.username:
            self.room = set()
        else:
            self.room.remove(user)
    def handle_invite(self, invitation, **kwargs):
        d = {'type': 'invite', 'invitation': invitation}
        d.update(kwargs)
        if not isinstance(invitation, str):
            self.croak("Malformed invite message: %s" % json.dumps(d))
        method = 'handle_invite_'+invitation
        if not hasattr(self, method):
            self.croak("Unhandled invitation type: %s" % json.dumps(d))
        return getattr(self, method)(**kwargs)
    def handle_revoke(self, invitation, **kwargs):
        d = {'type': 'revoke', 'invitation': invitation}
        d.update(kwargs)
        if not isinstance(invitation, str):
            self.croak("Malformed revoke message: %s" % json.dumps(d))
        method = 'handle_revoke_'+invitation
        if not hasattr(self, method):
            self.croak("Unhandled invitation type: %s" % json.dumps(d))
        return getattr(self, method)(**kwargs)
    def handle_accept(self, invitation, **kwargs):
        d = {'type': 'accept', 'invitation': invitation}
        d.update(kwargs)
        if not isinstance(invitation, str):
            self.croak("Malformed accept message: %s" % json.dumps(d))
        method = 'handle_accept_'+invitation
        if not hasattr(self, method):
            self.croak("Unhandled invitation type: %s" % json.dumps(d))
        return getattr(self, method)(**kwargs)
    def handle_reject(self, invitation, **kwargs):
        d = {'type': 'reject', 'invitation': invitation}
        d.update(kwargs)
        if not isinstance(invitation, str):
            self.croak("Malformed reject message: %s" % json.dumps(d))
        method = 'handle_reject_'+invitation
        if not hasattr(self, method):
            self.croak("Unhandled invitation type: %s" % json.dumps(d))
        return getattr(self, method)(**kwargs)
    def wait_for(self, **d):
        # Save all the messages we weren't waiting for, so that we can
        # replay them afterwards
        bottle = []
        try:
            while True:
                msg = self.read_msg()
                for k,v in d.items():
                    if msg.get(k) != v:
                        break
                else:
                    return msg
                if msg.get('type') == 'error':
                    raise Exception("Server error: %s" % (msg.get('message'),))
                bottle.append(msg)
        finally:
            # Restore the bottled-up messages
            self.buf = '\n'.join(map(json.dumps, bottle)) + self.buf
    def wall(self, msg):
        self.write_msg({'type': 'wall', 'message': str(msg)})
    def message(self, msg, to):
        self.write_msg({'type': 'message', 'message': str(msg), 'to': str(to)})
    def invite_game(self, to):
        self.write_msg({'type': 'invite', 'invitation': 'new', 'to': str(to)})
    def revoke_game(self, to):
        self.write_msg({'type': 'revoke', 'invitation': 'new', 'to': str(to)})
    def accept_game(self, to):
        self.write_msg({'type': 'accept', 'invitation': 'new', 'to': str(to)})
    def reject_game(self, to):
        self.write_msg({'type': 'reject', 'invitation': 'new', 'to': str(to)})
    def invite_join(self, to):
        self.write_msg({'type': 'invite', 'invitation': 'join', 'to': str(to)})
    def revoke_join(self, to):
        self.write_msg({'type': 'revoke', 'invitation': 'join', 'to': str(to)})
    def accept_join(self, to):
        self.write_msg({'type': 'accept', 'invitation': 'join', 'to': str(to)})
    def reject_join(self, to):
        self.write_msg({'type': 'reject', 'invitation': 'join', 'to': str(to)})
    def leave_game(self):
        self.write_msg({'type': 'part'})
        #self.wait_for(**{'type': 'part', 'from': self.username})
    def rename_team(self, team_name):
        self.write_msg({'type': 'team name', 'name': team_name})
    def claim_player(self, player_name):
        self.write_msg({'type': 'claim', 'player': player_name})
    def assign_player(self, player_name, username):
        self.write_msg({'type': 'assign', 'player': player_name, 'to': username})
    def disown_player(self, player_name):
        self.write_msg({'type': 'disown', 'player': player_name})
    def action(self, action, **d):
        msg = {'type': 'action', 'action': action}
        msg.update(d)
        self.write_msg(msg)
    def call_toss(self, tails):
        self.action('call toss', tails=tails)
    def call_heads(self):
        self.call_toss(False)
    def call_tails(self):
        self.call_toss(True)
    def flip_coin(self):
        self.action('flip coin')
    def choose_first(self, bat):
        self.action('choose first', bat=bat)
    def choose_bat_first(self):
        self.choose_first(True)
    def choose_field_first(self):
        self.choose_first(False)
    def choose_batsman(self, player_name):
        self.action('next bat', batsman=player_name)
    def choose_keeper(self, player_name):
        self.action('choose keeper', keeper=player_name)
    def choose_bowler(self, player_name, keeper=None):
        d = {'bowler': player_name}
        if keeper is not None:
            d['keeper'] = keeper
        self.action('choose bowler', **d)
    def field_swap(self, first_player, second_player):
        self.action('field assign', swap=(first_player, second_player))
    def field_done(self):
        self.action('field assign')
    def roll_dice(self):
        self.action('roll')

class ConsoleClient(Connection):
    def __init__(self, **kwargs):
        self.in_invite_new = set()
        self.in_invite_join = set()
        self.cons = sys.stdin
        self.halt = False
        self.dbg = kwargs.pop('debug', False)
        super(ConsoleClient, self).__init__(**kwargs)
        print("%s Server version %s" % (self.tagify(), '.'.join(map(str, self.server_version))))
        print("%s %s" % (self.tagify(), self.motd))
    def debug(self, cls, *args):
        if self.dbg:
            print("DBG %s: %s" % (cls, ' '.join(map(str, args))))
    def main(self):
        try:
            r, w, x = select.select((self.cons.fileno(),), (), (), 0)
            if self.cons.fileno() in r:
                inp = self.cons.readline().rstrip('\n')
                self.do_input(inp)
            if self.halt:
                return
            self.maybe_read_and_handle()
        except SocketClosed as e:
            print(e)
            self.halt = True
        except Croaked:
            self.halt = True
            raise
        except Exception as e:
            self.croak("main loop: %r" % e, True)
            self.halt = True
    def main_loop(self):
        while not self.halt:
            self.main()
    def do_blank(self):
        # Later this may be affected by the state machine
        # (e.g. to perform a requested trigger action)
        pass
    def do_plain_input(self, inp):
        # Later this may be affected by the state machine
        self.wall(inp)
    def do_input(self, inp):
        if not inp:
            return self.do_blank()
        if inp[0] != '/':
            return self.do_plain_input(inp)
        words = shlex.split(inp[1:])
        cmd, *args = words
        method = 'cmd_' + cmd
        if hasattr(self, method):
            try:
                return getattr(self, method)(*args)
            except Exception as e:
                print('Command handler: /%s:' % (cmd,), e)
                return
        print("Unrecognised command /%s" % cmd)
    def cmd_quit(self, *messages):
        self.goodbye(' '.join(messages) or 'Client quit')
        self.halt = True
    def cmd_invite(self, to):
        self.invite_game(to)
    def cmd_accept(self, to, what=None):
        if what is None:
            if to in self.in_invite_new:
                if to in self.in_invite_join:
                    raise Exception("Ambiguous - specify '/accept <user> new' or '/accept <user> join'")
                return self.accept_game(to)
            if to in self.in_invite_join:
                return self.accept_join(to)
            raise Exception("No invite outstanding for new or join from", to)
        if what == 'new':
            if to not in self.in_invite_new:
                print("No new-game invite outstanding from %s; trying anyway" % (to,))
            return self.accept_game(to)
        if what == 'join':
            if to not in self.in_invite_join:
                print("No join-game invite outstanding from %s; trying anyway" % (to,))
            return self.accept_join(to)
        raise Exception("<what> must be 'new' or 'join', not %s" % (what,))
    def cmd_reject(self, to, what=None):
        if what is None:
            if to in self.in_invite_new:
                if to in self.in_invite_join:
                    raise Exception("Ambiguous - specify '/reject <user> new' or '/reject <user> join'")
                return self.reject_game(to)
            if to in self.in_invite_join:
                return self.reject_join(to)
            raise Exception("No invite outstanding for new or join from", to)
        if what == 'new':
            if to not in self.in_invite_new:
                print("No new-game invite outstanding from %s; trying anyway" % (to,))
            return self.reject_game(to)
        if what == 'join':
            if to not in self.in_invite_join:
                print("No join-game invite outstanding from %s; trying anyway" % (to,))
            return self.reject_join(to)
        raise Exception("<what> must be 'new' or 'join', not %s" % (what,))
    def tagify(self, bracks='_', frm=None, w=16):
        if frm is None:
            tag = '-'
        else:
            tag = bracks[0] + frm + bracks[-1]
        return tag.rjust(w)
    def handle_error(self, message):
        print("error: %s" % (message,))
    def handle_wall(self, message, frm):
        print("%s %s" % (self.tagify('{}', frm), message))
    def handle_message(self, message, frm=None):
        print("%s %s" % (self.tagify('<>', frm), message))
    def handle_enter(self, user):
        super(ConsoleClient, self).handle_enter(user)
        print("%s entered the room" % (self.tagify('=', user),))
    def handle_exit(self, user):
        super(ConsoleClient, self).handle_exit(user)
        print("%s left the room" % (self.tagify('=', user),))
        # Revoke any outstanding invites
        self.in_invite_new.discard(user)
        self.in_invite_join.discard(user)
    def handle_invite_new(self, frm):
        print("%s invited you to start a game!  /accept or /reject it." % self.tagify('=', frm))
        self.in_invite_new.add(frm)
    def handle_invite_join(self, frm):
        print("%s invited you to join their team!  /accept or /reject it." % self.tagify('=', frm))
        self.in_invite_join.add(frm)
    def handle_revoke_new(self, frm):
        if frm not in self.in_invite_new:
            return # ignore it
        print("%s revoked the invitation to start a game." % self.tagify('=', frm))
        self.in_invite_new.remove(frm)
    def handle_revoke_join(self, frm):
        if frm not in self.in_invite_join:
            return # ignore it
        print("%s revoked the invitation to join their team." % self.tagify('=', frm))
        self.in_invite_join.remove(frm)
#    def handle_accept_new(self, frm):
#        

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Command-line client for networked Howzat game')
    parser.add_argument('-u', '--username', default=getpass.getuser())
    args = parser.parse_args()
    ConsoleClient(username=args.username, debug=True).main_loop()
