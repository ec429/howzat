# Rules of Extended Howzat

## Overview

Howzat simulates a Twenty20 cricket match, with all outcomes determined by
rolls of six-sided dice ('d6').  The basic structure of the game should be
familiar to any cricket fan.  Thus, these rules focus on how each
individual ball of the match is resolved.

## Turn sequence

The sequence for each ball is:

1. Bowler rolls a d6 to bowl the ball.
   * Bowler may have to roll a second d6 to resolve Extras.
2. Unless ball is a Wide, Batsman rolls a d6 to strike it.
3. If catch possible, Batsman rolls 2d6 to pick a Fielder.
4. If catch possible, Fielder rolls a d6 to attempt the catch.

### Bowling the ball

The bowler's d6 roll has two functions: on an appeal (see below) it
determines the wicket, otherwise it determines extras.

A roll of 1 will make the delivery a possible Extra, and the bowler must
roll another d6 to determine it:

1. No-Ball
2. Wide
3. Byes
4. Leg Byes

Any other roll is a legal delivery and any runs will be off the bat.

### Striking the ball

If the ball is a Wide, the batsman cannot strike it and does not roll.
(Thus, the batsmen cannot run additional byes off a wide, nor does the
ball ever go for five wides, even though it can go for four byes.)

Otherwise, the batsman's roll is interpreted as follows:

1. One run.  (Remember to change ends.)
2. Two runs.
3. No run (dot ball).
4. Four runs.
5. _Howzat!_
6. Six runs, **unless** Byes or Leg Byes in which case No run.

On a roll of 5 (_Howzat!_), the bowler's roll is then consulted:

1. Not Out.  (The ball may also have been an Extra.)
2. Bowled.
3. Possible catch; proceed to section [Catching the ball](#catching-the-ball).
4. Stumped.
5. Leg Before Wicket.
6. Run Out.

(An unfortunate limitation of this system is that it does not allow the
batsman to be Run Out off a No-Ball, which can occur in real cricket.)

### Catching the ball

The batsman rolls 2d6 to determine which fielder is under it.  (Fielding
position 7, the most likely, is the wicketkeeper; positions 2 and 12 are
the currently active bowlers.)  Then, that fielder rolls a d6 to attempt
the catch.  On a 1 or 2, the catch is dropped; on any other result, it is
successfully caught and the batsman is out.
