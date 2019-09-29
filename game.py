#!/usr/bin/env python3

print("[INFO] Welcome to Roller Knight!")
print("[INFO] Copyright 2019 by Dan Pope and Larry Hastings.")
print("[INFO] Initializing runtime...")

from ascend.settings import load_settings
import pygame
from wasabi2d import event, run

from ascend.sound import init_sound
from ascend.game import Game
from ascend.control import init_controls


@event
def update(dt, keyboard):
    game.update(dt, keyboard)
    game.level.proto_update(dt, keyboard)


SHIFT = pygame.KMOD_LSHIFT | pygame.KMOD_RSHIFT

@event
def on_key_down(key, mod):
    if key == key.F12:
        if mod & SHIFT:
            game.scene.toggle_recording()
        else:
            game.scene.screenshot()



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

game = Game(settings, "larry")
level = game.new()

run()  # keep this at the end of the file
