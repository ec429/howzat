# Howzat Network Protocol

## Overview

Protocol messages consist of JSON objects, terminated with newlines for
ease of parsing.  By default it uses TCP port 26214 (0x6666).

## Multiplexing

A client may represent multiple players (possibly even an entire team).
In that case, the client should use the `player` field of the message to
determine which player is e.g. being asked to roll; it will be added to
all action requests.

## Session initiation

Each client, on connecting to the server's TCP port, is sent a `welcome`
message, to which it responds with a `hello` supplying its username.  The
client is then placed in the lobby, and may invite another client to
commence a new game.

When a new game invitation is accepted, the two clients become the
captains of the two teams, and may invite other clients to join their team
as players, or assign additional players to any client on their team.

Once both teams have 11 assigned players, the game begins.  For the toss,
the captain who sent the invite calls, and the other captain flips.

## Session termination

When a client leaves, either by a Goodbye message or by the termination of
its TCP connection, the server's handling of this depends on what the
client was controlling.

* If the client was captaining a team in a game, that game will be paused
  until a client reconnects with the same username.  While a game is
  paused, existing action requests may be answered by clients but new ones
  must not be sent by the server.
  - When the client reconnects, it will be sent a sequence of messages to
    inform it that it is captaining a team in an active game and replay
    the game history.
  - If an action had been requested from the client, the request will be
    re-sent when the client reconnects.
* If the client was controlling players in a game, those players will be
  marked as zombies until a client reconnects with the same username.  If
  the game needs to request an action from a zombie player, it will send
  a private message to the team captain explaining this, and then wait for
  the player to either de-zombie or be reassigned to a new client.

## Messages

### Error messages

Client: `{'type': 'error', 'message': <message>}`

The client is malfunctioning and about to shut down.  `message` should
describe what went wrong; the server may include it in a generated Wall
message shown as coming from the client.

Server: `{'type': 'error', 'message': <message>}`

A client action failed, or, the server is malfunctioning and wishes to
inform clients before it shuts down.  In either case, `message` should
describe what went wrong; the client may display it to the user.

### Connection messages

#### Welcome

Server: `{'type': 'welcome', 'version': [<proto-version>, <server-version>, ...], 'message': <welcome-message>}`

Announces the server.  For this version of the protocol, `proto-version`
must be 1; `server-version...` are the integer components of the server's
version number, excluding the major version which must match the
`proto-version`.  (Thus _howzat_ version 1.2.5 would send
`'version': [1, 2, 5]` and speak version 1 of the protocol.)
`welcome-message` is a Message of the Day which a client may display to
the user.
If the client does not speak the specified `proto-version`, it must hang
up the TCP connection.

#### Hello

Client: `{'type': 'hello', 'username': <username>, 'player': <player-name>}`

Registers a client with the server.  If the `username` is not unique on
the server, registration will fail with an `error` message; the client may
either try again or hang up.
`player-name` is the name this client wishes to use for its Player when
creating or joining games; it may be omitted, in which case it defaults to
`username`.

#### Goodbye

Client: `{'type': 'goodbye', 'message': <message>}`

The client wishes to leave the server.  The server should respond by
hanging up the client's TCP connection.  The server may also include the
(optional) `message` in a generated Wall message shown as coming from the
client.

### Chat messages

#### Wall message

Client: `{'type': 'wall', 'message': <message>}`

Sends `message` as a chat to all occupants of the current room (which is
a game if the client is in one, otherwise the lobby).

Server: `{'type': 'wall', 'message': <message>, 'frm': <username>}`

A wall message from `username` was sent to a room containing the client.
Clients may display the `message` to the user.

#### Private message

Client: `{'type': 'message', 'message': <message>, 'to': <username>}`

Sends `message` as a chat to the specified `username`.

Server: `{'type': 'message', 'message': <message>, 'frm': <username>}`

A chat message from `username` (or, if `username` is omitted, a notice
from the server) was sent to the client.
Clients may display the `message` to the user.

### Lobby messages

#### Propose new game

Client: `{'type': 'invite', 'invitation': 'new', 'to': <username>}`

Invites `username` to create a new game with the client.

Server: `{'type': 'invite', 'invitation': 'new', 'frm': <username>}`

`username` invited the client to create a new game.

#### Invite player to existing game

Client: `{'type': 'invite', 'invitation', 'join', 'to': <username>}`

Invites `username` to join the team captained by the client.

Server: `{'type': 'invite', 'invitation', 'join', 'frm': <username>}`

The client was invited to join a team captained by `username`.

#### Accept invitation

Client: `{'type': 'join', 'invitation': <invitation>, 'to': <username>}`

Accept an outstanding `invitation` from `username`.

Server: `{'type': 'join', 'invitation': <invitation>, 'frm': <username>}`

An outstanding invitation from the client was accepted by `username`.
This message will typically be followed by another (broadcast to the room)
indicating the effect of the accepted invitation.

#### Reject invitation

Client: `{'type': 'reject', 'invitation': <invitation>, 'to': <username>}`

Reject an outstanding `invitation` from `username`.

Server: `{'type': 'reject', 'invitation': <invitation>, 'frm': <username>}`

An invitation from the client was rejected by `username` and is no longer
outstanding.

#### Revoke invitation

Client: `{'type': 'revoke', 'invitation': <invitation>, 'to': <username>}`

Revokes any outstanding invitations to `username` of the specified
`invitation` type.

Server: `{'type': 'revoke', 'invitation': <invitation>, 'frm': <username>}`

The invitation from `username` to the client of type `invitation` has been
revoked.

### Player and team management messages

#### Join game

Server: `{'type': 'join', 'frm': <username>, 'player': <player-name>, 'team': <captain-username>}`

`username` has joined the game and is controlling `player-name` on the
team captained by `captain-username`.

#### Leave game

Client: `{'type': 'part'}`

Leaves a game.  If the client is controlling any players, and the game has
already started, this will fail with an `error` message.  If the client is
controlling a team captain, the game will be abandoned.

Server: `{'type': 'part', 'frm': <username>}`

`username` left the game.  If they were controlling any players, `disown`
messages will have been generated first; thus, the server must not send
this message while `username` is still controlling players.

#### Rename team

Client: `{'type': 'team name', 'name': <team-name>}`

Sets the display name of the team captained by the client to `team-name`.
The client's username will still be used over the wire to refer to the
team.

Server: `{'type': 'team name', 'name': <team-name>, 'team': <captain-username>}`

The display name of the team captained by `captain-username` is now
`team-name`.  Clients may use this name for display purposes.

#### Rename player

Client: `{'type': 'rename', 'frm': <old-player-name>, 'to': <new-player-name>}`

Change `old-player-name`'s player name to `new-player-name`.  A captain
may rename any player on his team, and depending on permissions a client
may be able to rename players it controls.

Server: `{'type': 'rename', 'frm': <old-player-name>, 'to': <new-player-name>}`

`old-player-name`'s player name was changed to `new-player-name`.

#### Claim player

Client: `{'type': 'claim', 'player': <player-name>}`

Claim an additional player on the current team, and name it `player-name`.
Or, claim existing player `player-name` on the current team.
If this is not permitted, or the `player-name` is not unique in the
current game, this will fail with an `error` message.

#### Assign player

Client: `{'type': 'assign', 'player': <player-name>, 'to': <username>}`

Assign an additional player on the current team to `username`, and name it
`player-name`.  Or, assign existing player `player-name` on the current
team to `username`.
If the client is not the team captain, or the `player-name` is not unique
in the current game, this will fail with an `error` message.

Server: `{'type': 'assign', 'player': <player-name>, 'to': <username>, 'team': <captain-username>, 'new': true}`

An additional player was assigned to or claimed by `username`, and named
`player-name`, on the team captained by `captain-username`.

Server: `{'type': 'assign', 'player': <player-name>, 'to': <username>, 'team': <captain-username>, 'new': false}`

The existing player `player-name`, on the team captained by
`captain-username`, was assigned to or claimed by `username`.

#### Disown player

Client: `{'type': 'disown', 'player': <player-name>}`

Before the game has started, remove `player-name` from the current team.
Or, during the game, remove `player-name` from its current controller, and
mark it as a zombie.
If this is not permitted, or `player-name` is not on the team (client is
captain) or is not controlled by the client (otherwise), this will fail
with an `error` message.

Server: `{'type': 'disown', 'player': <player-name>, 'frm': <username>, 'team': <captain-username>}`

Player `player-name`, previously controlled by `username` and on the team
captained by `captain-username`, was removed.

### Game messages

#### Game begins

Server: `{'type': 'begin'}`

The game in which the client is currently joined has begun.

#### Trigger action

Client: `{'type': 'action', 'action': <action>}`

For actions which do not require additional input from the client, this
message suffices to perform `action`.  Where actions require a source of
randomness, the receipt time of this message will be used.

If a client sends an action (trigger or otherwise) which the server has
not requested, it will fail with an `error` message.

If the server has requested an action, but the client's attempt to perform
it fails with an `error` message, the server shall re-send the action
request.

#### Coin toss

Server: `{'type': 'action', 'action': 'call toss'}`

Requests the client to call Heads or Tails.
This request shall only be sent to the team captain.

Client: `{'type': 'action', 'action': 'call toss', 'heads': <bool>}`

Call either Heads (if `bool` is true) or Tails (if it is false).

Server: `{'type': 'action', 'action': 'flip coin', 'call': <bool>}`

Requests the client to perform a `flip coin` trigger action.
This request shall only be sent to the team captain.
The other captain has called Heads (if `bool` is true) or Tails (if it is
false).

Server: `{'type': 'toss', 'caller': <captain-username>, 'call': <call>, 'coin': <coin>}`

The coin was tossed and landed either Heads (if `coin` is true) or Tails
(if `coin` is false).  This was compared to the call of Heads (if `call`
is true) or Tails (if `call` is false) made by `captain-username`.

#### Toss winner's choice

Server: `{'type': 'action', 'action': 'choose first'}`

Requests the client to choose whether to bat or bowl.
This request shall only be sent to the team captain who has won the toss.

Client: `{'type': 'action', 'action': 'choose first', 'choice': <bat>}`

Chooses that the team shall bat first (if `bat` is true) or bowl/field
first (if `bat` is false).

Server: `{'type': 'choose first', 'batting': <captain-username>}`

The choice has been made, and `captain-username`'s team will bat first.

#### Choose batsman

Server: `{'type': 'action', 'action': 'next bat', 'legal': [<player-name>, ...]}`

Requests the client to select a player to bat.  The listed `player-name`s
are eligible.
This request shall only be sent to the team captain.

Client: `{'type': 'action', 'action': 'next bat', 'batsman': <player-name>}`

Send `player-name` out to bat.  If there is no player of that name on the
team, or the player has already batted or is currently batting, this will
fail with an `error` message.

Server: `{'type': 'next bat', 'team': <captain-username>, 'batsman': <player-name>, 'order': <i>}`

`player-name` goes out to bat, `i+1`^th^ in the order, for the team
captained by `captain-username`.

#### Choose wicketkeeper

Server: `{'type': 'action', 'action': 'choose keeper', 'legal': [<player-name>, ...]}`

Requests the client to select a player to be the team's wicketkeeper.
The listed `player-name`s are eligible.
This request shall only be sent to the team captain.

Client: `{'type': 'action', 'action': 'choose keeper', 'keeper': <player-name>}`

Selects `player-name` to be the wicketkeeper.  If there is no player of
that name on the team, this will fail with an `error` message.

Server: `{'type': 'choose keeper', 'team': <captain-username>, 'keeper': <player-name>}`

`player-name` is now the wicketkeeper of the team captained by
`captain-username`.

#### Choose bowler

Server: `{'type': 'action', 'action': 'choose bowler', 'legal': [<player-name>, ...], 'current': <current-bowler>}`

Requests the client to select a player to bowl the next over.
This request shall only be sent to the team captain.
The previous over from this end was bowled by `current-bowler` (this field
will be omitted for the first two overs), and the listed `player-name`s
are eligible to bowl.  (These will be all players who have bowled fewer
than their maximum number of overs for the match, except for the bowler of
the previous over from the other end if any.)

While this request is outstanding, `choose keeper` actions shall also be
accepted from the client.

Client: `{'type': 'action', 'action': 'choose bowler', 'bowler': <player-name>, 'keeper': <new-keeper>}`

Selects `player-name` to bowl the next over.
If there is no player of that name on the team, or that player is not
eligible to bowl or is currently keeping wicket, this will fail with an
`error` message.

Server: `{'type': 'choose bowler', 'team': <captain-username>, 'bowler': <player-name>, 'over': <i>}`

`player-name` will bowl the `i+1`^th^ over for the team captained by
`captain-username`.

#### Fielding assignments

Server: `{'type': 'action', 'action': 'field assign', 'fielders': [<player-name>, ...]}`

Requests the client to set up fielding assignments.
This request shall only be sent to the team captain.
The existing assignments (which may have been automatically changed) are
given in `fielders` as they would be in a `field assign` message (below).

Client: `{'type': 'action', 'action': 'field assign', 'swap': [<first-player>, <second-player>]}`

Swaps the fielding assignments of `first-player` and `second-player`.  If
either player is currently bowling, this will fail with an `error` message.

If either player is currently keeping, this will change the keeper to the
other player, generating a `choose keeper` message to the room.

If the action succeeds, another `action` `field assign` request will be
generated with the new assignments.

Client: `{'type': 'action', 'action': 'field assign'}`

Indicates that the client is done setting up field assignments.

Server: `{'type': 'field assign', 'team': <captain-username>, 'fielders': [<player-name>, ...]}`

The players of the team captained by `captain-username` have been assigned
to fielding positions in the order their `player-name`s are given in
`fielders`.  All eleven players of the team must be listed.  The first
position must be the current bowler, and the seventh must be the current
wicketkeeper.

#### Die roll

Server: `{'type': 'action', 'action': 'roll', 'dice': <count>, 'reason': <reason>}`

The client's player needs to roll `count` six-sided dice to resolve the
game event specified in `reason`.  Requests the client to do so with a
`roll` trigger action.

Server: `{'type': 'roll', 'player': <player-name>, 'dice': [<d6>, ...], 'reason': <reason>}`

`player-name` rolled some six-sided dice and obtained the results listed
in `dice`.  Each `d6` is an integer from 1 to 6.

#### Ball

Server: `{'type': 'ball', 'extra': <extra>, 'runs': <runs>, 'wicket': <mode>, 'catch': <catcher>, 'bowler': <bowler>, 'striker': <batsman>}`

A ball was bowled by `bowler` to `batsman`.  `runs` runs were added to the
batting total.  If `wicket` is present, `batsman` is out by `mode`, which
must be one of:

* `'bowled'`
* `'caught'`
* `'stumped'`
* `'lbw'`
* `'run out'`

Furthermore, if `mode` is `'caught'`, then `catcher` specifies the fielder
who took the catch.
`catch` may also be present when there is no `wicket`, in which case it
indicates that `catcher` dropped a catching chance.

If `extra` is present, it must be one of the following:

* `'nb'`.  The delivery was a No-Ball.
* `'w'`.  The delivery was a Wide.
* `'b'`.  The runs were Byes.  (`runs` must be nonzero.)
* `'lb'`.  The runs were Leg-Byes.  (`runs` must be nonzero.)

#### Fall of Wicket

Server: `{'type': 'fow', 'out': <striker>, 'score': <score>, 'not out': <non-striker>, 'nscore': <non-striker-score>, 'over': <i>, 'ball': <j>, 'wkts': <k>}`

The `k`^th^ wicket fell on the `j`^th^ legal delivery of the `i+1`^th^
over.  `striker` was out for `score`, while `non-striker` remained not out
on a score of `nscore`.

#### Over

Server: `{'type': 'over', 'over': <i>, 'total': <score>, 'for': <wkts>}`

The `i+1`^th^ over has completed and the score is now `score` for `wkts`.

#### Innings

Server: `{'type': 'innings', 'team': <captain-username>, 'over': <i>, 'ball': <j>, 'total': <score>, 'for': <wkts>}`

The innings of the team captained by `captain-username` ended on the
`j`^th^ legal delivery of the `i+1`^th^ over, with a final score of
`score` runs for `wkts` wickets.

#### Match

Server: `{'type': 'match', 'winner': <winner-username>, 'loser': <loser-username>, 'runs': <run-margin>}`

The game has ended.
The team captained by `winner-username` beat the team captained by
`loser-username` by `run-margin` runs.

Server: `{'type': 'match', 'winner': <winner-username>, 'loser': <loser-username>, 'wickets': <wkt-margin>}`

The game has ended.
The team captained by `winner-username` beat the team captained by
`loser-username` by `wkt-margin` wickets.
