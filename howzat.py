#!/usr/bin/python3
import random
import time

EXTRA_NB = 1
EXTRA_W = 2
EXTRA_B = 3
EXTRA_LB = 4

class Wicket(object):
    def __init__(self, how, who=None, cab=False):
        self.how = how
        self.who = who
        self.cab = cab
    @classmethod
    def roll(cls, bowl, bowler, batsman, field):
        print("Howzat?")
        # Not Out, bowled, caught, stumped, lbw, run out
        if bowl == 1: # Not Out
            return None
        if bowl == 2:
            return cls("bowled")
        if bowl == 3:
            # batsman: 2d6 to decide where he hits it.  12 goes to 1
            fielder = field[(batsman.roll_2d6(prompt="Roll 2d6 to pick fielder") - 1) % 11]
            print("In the air to %s..." % (fielder.name,))
            # fielder: roll d6 to catch, drop on 1 or 2
            if fielder.roll_d6(prompt="Roll to attempt the catch") > 2:
                return cls("caught", fielder, fielder == bowler)
            print("Dropped it!")
            return None
        if bowl == 4:
            # Wicketkeeper is a roll of 7 on the 2d6
            return cls("stumped", field[6])
        if bowl == 5:
            return cls("lbw")
        if bowl == 6:
            return cls("run out")
        raise Exception("This d6 has a %d?" % (bowl,))
    def __str__(self):
        if self.how == 'caught' and  self.cab:
            return 'caught & bowled'
        if self.who:
            return '%s %s' % (self.how, self.who.name)
        return self.how

class Ball(object):
    def __init__(self, bowler, batsman, runs, wicket=None, extra=None):
        self.bowler = bowler
        self.batsman = batsman
        self.runs = runs
        self.wicket = wicket
        self.nb = extra == EXTRA_NB
        self.w = extra == EXTRA_W
        self.b = extra == EXTRA_B
        self.lb = extra == EXTRA_LB
        if extra == EXTRA_NB:
            print("No-Ball called")
        elif extra == EXTRA_W:
            print("Wide ball")
        # No sixes off potential Extras; dot ball instead
        if (extra is not None) and self.runs == 6:
            self.runs = 0
        if not self.runs:
            self.b = False
            self.lb = False
        if self.b:
            print("Byes taken")
        elif self.lb:
            print("Leg Byes taken")
        self.total_runs = self.runs + int(self.nb) + int(self.w)
        self.bat_runs = 0 if self.b or self.lb else self.runs
        self.bwl_runs = 0 if self.b or self.lb else self.total_runs
        self.legal = not self.nb and not self.w
    @classmethod
    def roll(cls, bowler, batsman, field):
        bowl = bowler.roll_d6(prompt="Roll to bowl to "+batsman.name)
        extra = None
        if bowl == 1:
            # possible Extra; roll again
            extra = bowler.roll_d6(prompt="Roll for extras")
        if extra == EXTRA_W: # Batsman does not roll
            return cls(bowler, batsman, 0, extra=extra)
        bat = batsman.roll_d6(prompt="Roll to play the ball")
        if bat == 5: # Wicket
            return cls(bowler, batsman, 0, Wicket.roll(bowl, bowler, batsman, field), extra=extra)
        if bat == 3: # No run
            return cls(bowler, batsman, 0, extra=extra)
        return cls(bowler, batsman, bat, extra=extra)
    def __str__(self):
        if self.wicket:
            if self.wicket.how == 'run out':
                return '>> run  out'
            return '>> %s  %s' % (self.wicket, self.bowler.name)
        if self.nb:
            if self.runs:
                # U+2460 CIRCLED DIGIT ONE and friends
                return chr(0x245f + self.runs)
            # U+25CB WHITE CIRCLE
            return chr(0x25CB)
        if self.w:
            return '+'
        if self.runs:
            if self.b:
                # U+25B3 WHITE UP-POINTING TRIANGLE
                return "%s%d" % (chr(0x25b3), self.runs)
            if self.lb:
                # U+25BD WHITE DOWN-POINTING TRIANGLE
                return "%s%d" % (chr(0x25bd), self.runs)
            return str(self.runs)
        return '.'
    def batstr(self):
        if self.wicket:
            # U+00BB RIGHT-POINTING DOUBLE ANGLE QUOTATION MARK
            if self.wicket.how == 'run out':
                return chr(0xbb)+' run  out'
            return chr(0xbb)+' %s  %s' % (self.wicket, self.bowler.name)
        if self.w:
            return ''
        if self.b or self.lb:
            return '.'
        if self.runs:
            return '%d' % (self.runs,)
        if self.nb:
            return ''
        return '.'
    def bowlstr(self):
        if self.wicket:
            if self.wicket.how == 'run out':
                return '.'
            return 'W'
        if self.nb:
            if self.runs:
                # U+2460 CIRCLED DIGIT ONE and friends
                return chr(0x245f + self.runs)
            # U+25CB WHITE CIRCLE
            return chr(0x25CB)
        if self.w:
            return '+'
        if self.b:
            return chr(0x25b3)
        if self.lb:
            return chr(0x25bd)
        if self.runs:
            return str(self.runs)
        return '.'

class Over(object):
    def __init__(self, inns):
        self.bowler = inns.bowling
        self.balls = []
        self.bowler.bowling.append(self)
        self.nb = 0
        self.w = 0
        self.runs = 0
        self.wkts = 0
        self.to_come = 6
    def deliver(self, ball):
        self.balls.append(ball)
        if ball.nb:
            self.nb += 1
        elif ball.w:
            self.w += 1
        else:
            self.to_come -= 1
        if ball.wicket and ball.wicket.how != 'run out':
            self.wkts += 1
        self.runs += ball.bwl_runs
    def ofrac(self, ps=False):
        if not self.to_come and not ps:
            return ""
        return ".%d" % (6 - self.to_come,)
    def over(self, onum, ps=False):
        if self.to_come:
            onum -= 1
        return "%d%s" % (onum, self.ofrac(ps))

class Innings(object):
    def __init__(self, batting, fielding, chasing=None):
        self.bteam = batting
        self.fteam = fielding
        self.chasing = chasing
        self.border = list(self.bteam.border)
        self.non_striker = self.border.pop(0)
        self.striker = self.border.pop(0)
        self.resting = None
        self.bowling = None
        self.total = 0
        self.b = 0 # Byes
        self.lb = 0 # Leg Byes
        self.fow = []
        self.overs = []
        self.new_over()
        self.in_play = True
    def legal_bowlers(self, last):
        return [p for p in self.fteam.players if len(p.bowling) < 4 and p != last]
    def swap_strike(self):
        self.striker, self.non_striker = self.non_striker, self.striker
    def new_over(self):
        self.bowling, self.resting = self.resting, self.bowling
        self.fteam.field[0], self.fteam.field[1] = self.fteam.field[1], self.fteam.field[0]
        legal = self.legal_bowlers(self.resting)
        if self.bowling not in legal or self.fteam.captain.change_bowler(self.bowling):
            bowl = self.fteam.captain.choose_bowler(legal)
            bi = self.fteam.field.index(bowl)
            self.fteam.field[0], self.fteam.field[bi] = self.fteam.field[bi], self.fteam.field[0]
            self.bowling = bowl
        if self.bowling.keeper:
            keep = self.fteam.captain.choose_keeper([p for p in self.fteam if p != self.bowling])
            ki = self.fteam.field.index(keep)
            self.bowling.keeper = False
            keep.keeper = True
            self.fteam.field[ki], self.fteam.field[6] = self.fteam.field[6], self.fteam.field[ki]
        self.swap_strike()
        self.overs.append(Over(self))
        if self.chasing is None:
            chase = ""
        else:
            chase = " - %d required" % (self.chasing + 1 - self.total)
        print("Over %d; %d/%d.  %s to %s (%s off strike)%s" % (len(self.overs), self.total, len(self.fow), self.bowling.name, self.striker.name, self.non_striker.name, chase))
        if not self.bowling.first_over:
            self.bowling.first_over = len(self.overs)
    @property
    def over(self):
        return self.overs[-1]
    @property
    def odesc(self):
        return self.over.over(len(self.overs))
    def bowl(self):
        if not self.over.to_come:
            self.new_over()
        ball = Ball.roll(self.bowling, self.striker, self.fteam.field)
        self.over.deliver(ball)
        self.striker.innings.append(ball)
        print(str(ball))
        if ball.wicket:
            self.striker.out = ball
            self.fow.append((self.striker, self.total, self.odesc))
            if self.border:
                self.striker = self.border.pop(0)
            else:
                self.in_play = False
        elif ball.runs % 2:
            self.swap_strike()
        self.total += ball.total_runs
        if ball.b:
            self.b += ball.runs
        elif ball.lb:
            self.lb += ball.runs
        # Twenty20
        if not self.over.to_come and len(self.overs) == 20:
            self.in_play = False
        if self.chasing is not None and self.total > self.chasing:
            self.in_play = False
    def batting_summary(self):
        if self.chasing is not None:
            print("Chasing %d" % (self.chasing,))
        for bat in self.bteam.border:
            if bat in self.border:
                print("%s  did not bat" % (bat.name,))
            else:
                print("%s  %s  %s%d (%d)" % (bat.name, ''.join(b.batstr() for b in bat.innings).replace('..', ':'), '' if bat.out else 'not  out  ', bat.score, bat.faced))
        def sfow(fow):
            i, fow = fow
            bat, tot, ovs = fow
            return '%s %d/%d (%s)' % (bat.name, tot, i + 1, ovs)
        print("Extras: %dnb %dw %db %dlb" % (sum(o.nb for o in self.overs),
                                             sum(o.w for o in self.overs),
                                             self.b, self.lb))
        if len(self.fow) == 10:
            fer = " all out"
        else:
            fer = "/%d" % (len(self.fow),)
        print("Total: %d%s (%s ovs)" % (self.total, fer, self.odesc))
        print("FOW: %s" % ('; '.join(map(sfow, enumerate(self.fow)))))
    def bowling_summary(self):
        for bwl in sorted(self.fteam.field, key=lambda p:p.first_over):
            if bwl.bowling:
                over = bwl.bowling[-1]
                exes = []
                if bwl.nb:
                    exes.append("%dnb" % (bwl.nb,))
                if bwl.w:
                    exes.append("%dw" % (bwl.w,))
                if exes:
                    exs = ' (%s)' % (' '.join(exes),)
                else:
                    exs = ''
                # Bowling Analysis
                banal = ' '.join(''.join(b.bowlstr() for b in o.balls) for o in bwl.bowling)
                print("%s: %s  %so %dm %d/%d%s" % (bwl.name, banal, over.over(len(bwl.bowling)), bwl.maidens, bwl.runs, bwl.wkts, exs))

class Player(object):
    def __init__(self, name):
        self.name = name
        self.innings = []
        self.bowling = []
        self.out = None
        self.keeper = False
        self.first_over = 0
    def flip_coin(self, prompt=None):
        return bool(self.randint(0, 1))
    def do_roll_d6(self, prompt=None):
        return self.randint(1, 6, prompt=prompt)
    def roll_d6(self, prompt=None):
        r = self.do_roll_d6(prompt)
        print("%s rolled d6 %s" % (self.name, chr(0x267f + r)))
        return r
    def roll_2d6(self, prompt=None):
        pa = prompt + " (1)" if prompt else None
        pb = prompt + " (2)" if prompt else None
        a = self.do_roll_d6(prompt=pa)
        b = self.do_roll_d6(prompt=pb)
        r = a + b
        print("%s rolled 2d6 %s%s -> %d" % (self.name, chr(0x267f + a), chr(0x267f + b), r))
        return r
    # Batting stats
    @property
    def score(self):
        return sum(b.bat_runs for b in self.innings)
    @property
    def faced(self):
        return len([b for b in self.innings if b.legal])
    # Bowling stats
    @property
    def wkts(self):
        return sum(o.wkts for o in self.bowling)
    @property
    def runs(self): # conceded
        return sum(o.runs for o in self.bowling)
    @property
    def maidens(self):
        return len([o for o in self.bowling if not o.runs and not o.to_come])
    @property
    def nb(self):
        return sum(o.nb for o in self.bowling)
    @property
    def w(self):
        return sum(o.w for o in self.bowling)

class DeterministicPlayer(Player):
    def __init__(self, name):
        super(DeterministicPlayer, self).__init__(name)
        # Seed the RNG with our name
        self.rng = random.Random(self.name)
    def randint(self, a, b, prompt=None):
        return self.rng.randint(a, b)
    def call_toss(self):
        # Just always call Heads
        return False
    def choose_to_bat(self):
        # Always bat first
        return True
    def change_bowler(self, curr):
        # Don't change bowling unless you have to
        return False
    def choose_bowler(self, legal):
        nk = [p for p in legal if not p.keeper]
        # Always pick the lowest-batting legal bowler, excluding the keeper
        return nk[-1]
    def choose_keeper(self, legal):
        # Select #7 batsman as keeper
        return legal[6]

class RandomPlayer(Player):
    def __init__(self, name):
        super(RandomPlayer, self).__init__(name)
        self.rng = random.Random(time.time())
    def randint(self, a, b, prompt=None):
        return self.rng.randint(a, b)
    def call_toss(self):
        return self.randint(0, 1)
    def choose_to_bat(self):
        return self.randint(0, 1)
    def change_bowler(self, curr):
        # 1 in 3 chance to change bowler without being forced
        return not self.randint(0, 2)
    def choose_bowler(self, legal):
        nk = [p for p in legal if not p.keeper]
        # Prefer lower-batting players as bowlers
        return self.rng.choice(nk + nk[-4:])
    def choose_keeper(self, legal):
        # Select #7 batsman as keeper
        return legal[6]

class ConsolePlayer(Player):
    def randint(self, a, b, prompt=None):
        n = b + 1 - a
        # Wait for newline
        input(prompt if prompt else "Roll")
        # Six-part millisecond wheel
        t = time.time() % 0.001
        return (int(t * 1000.0 * n) % n) + a
    def call_toss(self):
        print("Heads or Tails?")
        while True:
            l = input().strip().lower()
            if l in ("heads", "h"):
                return False
            if l in ("tails", "t"):
                return True
            print("Please specify either Heads or Tails.")
    def choose_to_bat(self):
        print("Bat or bowl first?")
        while True:
            l = input().strip().lower()
            if l == "bat":
                return True
            if l in ("bowl", "field"):
                return False
            print("Please specify either Bat, Bowl or Field.")
    def yn(self):
        while True:
            l = input().strip().lower()
            if l in ("yes", "y", "true", "t"):
                return True
            if l in ("no", "n", "false", "f"):
                return False
            print("Please enter Y or N.")
    def change_bowler(self, curr):
        print("%s still has overs left.  Change bowler?" % (curr.name,))
        return self.yn()
    def choose_bowler(self, legal):
        print("Choose a bowler.  Available: %s." % ', '.join(p.name for p in legal))
        while True:
            l = input().strip().lower()
            for p in legal:
                if p.name.lower() == l:
                    if p.keeper:
                        print("%s is currently keeping wicket.  Are you sure?" % (p.name,))
                        if not self.yn():
                            print("Choose a bowler.")
                            break
                    return p
            else:
                print("Player not found.  Please choose a bowler from the available list.")
    def choose_keeper(self, legal):
        print("Choose a wicketkeeper.\nAvailable: %s." % ', '.join(p.name for p in legal))
        while True:
            l = input().strip().lower()
            for p in legal:
                if p.name.lower() == l:
                    return p
            else:
                print("Player not found.  Please choose a wicketkeeper from the available list.")

class Team(object):
    def __init__(self, name, players):
        assert len(players) == 11, players
        self.name = name
        self.players = players
        self.captain = self.players[0]
        # For now, hardcode the batting-order and fielding-positions
        self.border = list(players)
        self.field = list(players)
        keep = self.captain.choose_keeper(self.field)
        keep.keeper = True
        ki = self.field.index(keep)
        self.field[6], self.field[ki] = self.field[ki], self.field[6]
    @classmethod
    def rand(cls, prefix):
        return cls("Randoms", [RandomPlayer("%s%d" % (prefix, i + 1)) for i in range(11)])
    @classmethod
    def det(cls, prefix):
        return cls(prefix, [DeterministicPlayer("%s%d" % (prefix, i + 1)) for i in range(11)])
    @classmethod
    def cons(cls, prefix):
        return cls("Console player", [ConsolePlayer("%s%d" % (prefix, i + 1)) for i in range(11)])

def toss(TA, TB):
    # captains
    CA = TA.captain
    CB = TB.captain
    # True is Tails
    call = CA.call_toss()
    print("%s called %s" % (CA.name, "tails" if call else "heads"))
    coin = CB.flip_coin()
    print("The coin landed %s up" % ("tails" if coin else "heads"))
    if call == coin:
        if CA.choose_to_bat():
            print("%s won the toss and elected to bat" % (TA.name,))
            return (TA, TB)
        print("%s won the toss and elected to field" % (TA.name,))
        return (TB, TA)
    if CB.choose_to_bat():
        print("%s won the toss and elected to bat" % (TB.name,))
        return (TB, TA)
    print("%s won the toss and elected to field" % (TB.name,))
    return (TA, TB)

def play_match(TA, TB):
    TA, TB = toss(TA, TB)
    IA = Innings(TA, TB)
    while IA.in_play:
        IA.bowl()
    print()
    IA.batting_summary()
    IA.bowling_summary()
    print()
    IB = Innings(TB, TA, IA.total)
    while IB.in_play:
        IB.bowl()
    print()
    IB.batting_summary()
    IB.bowling_summary()
    print()
    if IA.total > IB.total:
        print("%s beat %s by %d runs" % (TA.name, TB.name, IA.total - IB.total))
    elif IB.total > IA.total:
        print("%s beat %s by %d wickets" % (TB.name, TA.name, 1 + len(IB.border)))
    else:
        print("%s and %s tied" % (TA.name, TB.name))

def test():
    """Test-run: play a match between two placeholder teams"""
    TA = Team.det("TA")
    TB = Team.det("TB")
    play_match(TA, TB)

def cons_vs_rand():
    """Console player versus random player"""
    TA = Team.cons("Con")
    TB = Team.rand("Opp")
    play_match(TA, TB)

if __name__ == '__main__':
    cons_vs_rand()
