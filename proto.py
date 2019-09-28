#!/usr/bin/env python3

print("[INFO] Initializing runtime...")

import sys
import math
import random
from pathlib import Path

import ascend
from ascend.settings import load_settings
import pygame

from wasabi2d import Scene, run, event, keys, sounds
import pygame.mouse
from pygame import joystick
from ascend.triangle_intersect import polygon_collision
from ascend.vector2d import Vector2D, Polar2D

from ascend.knight import Knight
from ascend.mobs import MagicMissile, Skeleton
from ascend.sound import init_sound
from ascend.game import Game
from ascend.control import init_controls




@event
def update(dt, keyboard):
    game.update(dt, keyboard)
    game.world.proto_update(dt, keyboard)


SHIFT = pygame.KMOD_LSHIFT | pygame.KMOD_RSHIFT

@event
def on_key_down(key, mod):
    if key == key.F12:
        if mod & SHIFT:
            game.scene.toggle_recording()
        else:
            game.scene.screenshot()

    if game.paused and (key == key.SPACE):
        close_game(game)
        new_game(game)



# reminder:
#
# (0, 0) is the upper left
#
# (0, 0)---------------------------+
# |                                |
# |                                |
# |                                |
# |                                |
# |                                |
# |                                |
# |                                |
# +----------------------(1024, 768)

settings = load_settings()
init_sound(settings)
init_controls(settings)

game = Game(settings)
game.create_scene()
game.create_world()


game.new_game()

run()  # keep this at the end of the file
