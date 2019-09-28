from wasabi2d import Scene, run, event
from ascend import game
import pygame

from ascend.settings import load_settings
from ascend.sound import init_sound


settings = load_settings()

scene = Scene(
    title="Ascent - PyWeek 28",
    width=1024,
    height=768
)

game.setup_scene(scene)
world = game.create_world(scene)
game.create_players(world)
world.spawn_mobs(num=20)


SHIFT = pygame.KMOD_LSHIFT | pygame.KMOD_RSHIFT


@event
def on_key_down(key, mod):
    if key == key.F12:
        if mod & SHIFT:
            scene.toggle_recording()
        else:
            scene.screenshot()


run()
