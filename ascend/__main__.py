from wasabi2d import Scene, run, event
from ascend import game
import pygame

from ascend.settings import load_settings
from ascend.sound import init_sound


settings = load_settings()

game = game.Game(settings, "dan")
level = game.new()


SHIFT = pygame.KMOD_LSHIFT | pygame.KMOD_RSHIFT


@event
def on_key_down(key, mod):
    if key == key.F12:
        if mod & SHIFT:
            scene.toggle_recording()
        else:
            scene.screenshot()


run()
