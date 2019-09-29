# Roller Knight

A devilishly hard game of melee combat

Copyright 2019 Daniel Pope and Larry Hastings

## Overview

Ah, good, you're here!  The prince is trapped at the top of the tower!
Please go rescue him!

You are a knight with a magic sword--but the sword only works when
you're moving really fast!  So you've strapped roller skates to your
armor.  The good news is now you can use your sword--the bad news is
it can be hard to control when you're moving that fast!

## Running Roller Knight

Run "`python3 game.py`" in the Roller Knight directory.
Make sure all the requirements are installed first!

If you're having framerate issues, you can turn off all
particles with the "`--no-particles`" option.  Sadly the
game is way less pretty without particles, but it may
help running the game on older machines.  Just run it as
"`python3 game.py --no-particle`".

Also, you can specify which level you want to start at,
as a single positional command-line argument.  For example,
to jump directly to level 6, you'd run "`python3 game.py 6`".
And to jump to level 10 of Endless mode,
run "`python3 game.py 'Endless 10'`".

## Gameplay

Roller Knight support keyboard controls (WASD) and joysticks.
Simply move in the direction you want to go; your Roller Knight
will rotate to face that direction.

When you're moving fast enough, your sword will glow!  This
creates a sort of arc of protection directly in front of you.
So you'll be safe as long as the bad guys--or the bullets--are
directly in front of you.  But watch out for bad guys crowding
in on the sides!

You can also fire off bombs, with the space bar or joypad button.
But you only have a limited number of bombs!  Although you can
occasionally pick up extra bomb powerups.

## Technology

Roller Knight was written using the excellent new *wasabi2d*
library by Dan Pope.

## Release History

### v1.0.1

* Fixed bug: pressing the space bar always started a new game.

* Added `--no-particles` command-line option.


### v1.0.0

Initial release.