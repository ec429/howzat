#!/usr/bin/python3
import random

class Wicket(object):
    def __init__(self, how, who=None, cab=False):
        self.how = how
        self.who = who
        self.cab = cab
    @classmethod
    def roll(cls, bowler, batsman, field):
        print("Howzat?")
        bowl = bowler.roll_d6()
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
    def __init__(self, bowler, batsman, runs, wicket=None):
        self.bowler = bowler
        self.batsman = batsman
        self.runs = runs
        self.wicket = wicket
    @classmethod
    def roll(cls, bowler, batsman, field):
        bat = batsman.roll_d6()
        if bat == 5: # Wicket
            return cls(bowler, batsman, 0, Wicket.roll(bowler, batsman, field))
        if bat == 3: # No run
            return cls(bowler, batsman, 0)
        return cls(bowler, batsman, bat)
    def __str__(self):
        if self.wicket:
            if self.wicket.how == 'run out':
                return '>> run  out'
            return '>> %s  %s' % (self.wicket, self.bowler.name)
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
            print("%s rolled d6 -> %d" % (self.name, r))
        return r
    def roll_2d6(self):
        r = self.roll_d6(False) + self.roll_d6(False)
        print("%s rolled 2d6 -> %d" % (self.name, r))
        return r
    @property
    def score(self): # with bat
        return sum(b.runs for b in self.innings)
    @property
    def balls(self): # bowling
        all_balls = []
        for o in self.bowling:
            all_balls.extend(o.balls)
        return all_balls
    @property
    def wkts(self):
        return len([b for b in self.balls if b.wicket and b.wicket.how != 'run out'])
    @property
    def runs(self): # conceded as bowler
        return sum(b.runs for b in self.balls)
    @property
    def maidens(self):
        return len([o for o in self.bowling if not sum(b.runs for b in o.balls) and not o.to_come])

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
    @property
    def to_come(self):
        return 6 - len(self.balls)

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
    def total(self):
        return sum(bat.score for bat in self.bteam.border)
    def bowl(self):
        if not self.over.to_come:
            self.new_over()
        ball = Ball.roll(self.bowling, self.striker, self.fteam.field)
        self.over.balls.append(ball)
        self.striker.innings.append(ball)
        print("%s %s" % (self.striker.name, ball))
        if ball.wicket:
            self.striker.out = ball
            self.fow.append((self.striker, self.total, "%d.%d" % (len(self.overs) - 1, len(self.over.balls))))
            if self.border:
                self.striker = self.border.pop(0)
            else:
                self.in_play = False
        elif ball.runs % 2:
            self.swap_strike()
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
                print("%s: did not bat" % (bat.name,))
            else:
                print("%s: %s  %s%d (%d)" % (bat.name, ' '.join(map(str, bat.innings)), '' if bat.out else 'not  out  ', bat.score, len(bat.innings)))
        if self.over.to_come:
            overs = "%d.%d" % (len(self.overs) - 1, len(self.over.balls))
        else:
            overs = "%d" % (len(self.overs),)
        def sfow(fow):
            i, fow = fow
            bat, tot, ovs = fow
            return '%d %s %d (%s)' % (i + 1, bat.name, tot, ovs)
        print("FOW: %s" % ('; '.join(map(sfow, enumerate(self.fow)))))
        if len(self.fow) == 10:
            fer = " all out"
        else:
            fer = "/%d" % (len(self.fow),)
        print("Total: %d%s (%s ovs)" % (self.total, fer, overs))
    def bowling_summary(self):
        for bwl in self.fteam.field:
            if bwl.bowling:
                over = bwl.bowling[-1]
                if over.to_come:
                    overs = "%d.%d" % (len(bwl.bowling) - 1, len(over.balls))
                else:
                    overs = "%d" % (len(bwl.bowling),)
                print("%s: %s %d %d %d" % (bwl.name, overs, bwl.maidens, bwl.runs, bwl.wkts))

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
