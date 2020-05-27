#!/usr/bin/python3
import random

EXTRA_NB = 1
EXTRA_W = 2
EXTRA_B = 3
EXTRA_LB = 4
EXTRA_MAX = 5

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
            fielder = field[(batsman.roll_2d6() - 1) % 11]
            print("In the air to %s..." % (fielder.name,))
            # fielder: roll d6 to catch, drop on 1 or 2
            if fielder.roll_d6() > 2:
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
        # No sixes off Byes or Leg Byes; dot ball instead
        if (self.b or self.lb) and self.runs == 6:
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
    @classmethod
    def roll(cls, bowler, batsman, field):
        bowl = bowler.roll_d6()
        extra = None
        if bowl == 1:
            # possible Extra; roll again
            extra = bowler.roll_d6()
            if extra >= EXTRA_MAX:
                extra = None
        if extra == EXTRA_W: # Batsman does not roll
            return cls(bowler, batsman, 0, extra=extra)
        bat = batsman.roll_d6()
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

class Player(object):
    def __init__(self, name):
        self.name = name
        self.innings = []
        self.bowling = []
        self.rng = random.Random(hash(self.name))
        self.out = None
    def roll_d6(self, _print=True):
        r = self.rng.randint(1, 6)
        if _print:
            # U+2680 DIE FACE-1 and friends
            print("%s rolled d6 %s" % (self.name, chr(0x267f + r)))
        return r
    def roll_2d6(self):
        a = self.roll_d6(False)
        b = self.roll_d6(False)
        r = a + b
        print("%s rolled 2d6 %s%s -> %d" % (self.name, chr(0x267f + a), chr(0x267f + b), r))
        return r
    @property
    def score(self): # with bat
        return sum(b.bat_runs for b in self.innings)
    @property
    def wkts(self):
        return sum(o.wkts for o in self.bowling)
    @property
    def runs(self): # conceded as bowler
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

class Team(object):
    def __init__(self, name, players):
        assert len(players) == 11, players
        self.name = name
        self.players = players
        # For now, hardcode the batting-order and fielding-positions
        self.border = list(players)
        self.field = list(players)
    @classmethod
    def short(cls, prefix):
        return cls(prefix, [Player("%s%d" % (prefix, i + 1)) for i in range(11)])

TA = Team.short("TA")
TB = Team.short("TB")

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
        return "%d%s" % (onum, self.ofrac(ps))

class Innings(object):
    def __init__(self, batting, fielding, chasing=None):
        self.bteam = batting
        self.fteam = fielding
        self.chasing = chasing
        self.border = list(self.bteam.border)
        self.non_striker = self.border.pop(0)
        self.striker = self.border.pop(0)
        # For now, first two fielders do all the bowling
        # TODO UI to let the fielding captain change this
        self.resting = self.fteam.field[0]
        self.bowling = self.fteam.field[1]
        self.total = 0
        self.b = 0 # Byes
        self.lb = 0 # Leg Byes
        self.overs = []
        self.new_over()
        self.fow = []
        self.in_play = True
    def swap_strike(self):
        self.striker, self.non_striker = self.non_striker, self.striker
    def new_over(self):
        self.bowling, self.resting = self.resting, self.bowling
        self.swap_strike()
        self.overs.append(Over(self))
        print("Over %d; %s to %s" % (len(self.overs), self.bowling.name, self.striker.name))
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
        print("%s %s" % (self.striker.name, ball))
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
                print("%s  %s  %s%d (%d)" % (bat.name, ''.join(b.batstr() for b in bat.innings).replace('..', ':'), '' if bat.out else 'not  out  ', bat.score, len(bat.innings)))
        def sfow(fow):
            i, fow = fow
            bat, tot, ovs = fow
            return '%d %s %d (%s)' % (i + 1, bat.name, tot, ovs)
        print("Extras: %dnb %dw %db %dlb" % (sum(o.nb for o in self.overs),
                                             sum(o.w for o in self.overs),
                                             self.b, self.lb))
        print("FOW: %s" % ('; '.join(map(sfow, enumerate(self.fow)))))
        if len(self.fow) == 10:
            fer = " all out"
        else:
            fer = "/%d" % (len(self.fow),)
        print("Total: %d%s (%s ovs)" % (self.total, fer, self.odesc))
    def bowling_summary(self):
        for bwl in self.fteam.field:
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
