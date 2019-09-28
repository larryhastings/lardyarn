from wasabi2d import Scene, event, run, clock
import pygame
from pygame import joystick
from pathlib import Path


import ascend

from .knight import KnightController
from .control import JoyController, KeyboardController, init_controls
from .constants import Layers
from .world import World


# __all__ = [
#     'run',
#     'create_players',
# ]


def setup_scene(scene):
    scene.background = (0.2, 0.2, 0.2)
    scene.layers[Layers.WALL_LAYER].set_effect(
        'dropshadow',
        radius=2,
        offset=(1.5, 1.5)
    )
    scene.layers[Layers.WALL_LAYER].set_effect(
        'dropshadow',
        radius=3,
        offset=(3, 3)
    )
    scene.layers[Layers.LOWER_EFFECTS_LAYER].set_effect(
        'bloom',
        radius=10,
    )

    smoke = scene.layers[Layers.LOWER_EFFECTS_LAYER].add_particle_group(
        texture='smoke',
        grow=0.1,
        max_age=0.8,
        drag=0.1,
    )
    smoke.add_color_stop(0, '#888888ff')
    smoke.add_color_stop(0.6, '#888888ff')
    smoke.add_color_stop(0.8, '#88888800')
    scene.smoke = smoke

    sparks = scene.layers[Layers.UPPER_EFFECTS_LAYER].add_particle_group(
        texture='spark',
        grow=0.1,
        max_age=0.6,
        drag=0.7,
    )
    sparks.add_color_stop(0, (2, 2, 0.8, 1))
    sparks.add_color_stop(0.3, (2, 1, 0, 1))
    sparks.add_color_stop(0.6, (0, 0, 0, 0))
    scene.sparks = sparks

    scene.bones = scene.layers[Layers.DEBRIS_LAYER].add_particle_group(
        texture='bone',
        max_age=4,
        drag=0.1,
        spin_drag=0.4,
    )
    scene.skulls = scene.layers[Layers.DEBRIS_LAYER].add_particle_group(
        texture='skull',
        max_age=4,
        drag=0.1,
        spin_drag=0.4,
    )
    for pgroup in (scene.bones, scene.skulls):
        pgroup.add_color_stop(0, '#bbbbbbff')
        pgroup.add_color_stop(1, '#bbbbbbff')
        pgroup.add_color_stop(4, '#bbbbbb00')


controllers = []


def create_players(world):
    player1 = KnightController(world.spawn_pc())

    if joystick.get_count() > 0:
        controllers.append(
            JoyController(player1, joystick.Joystick(0))
        )
    else:
        controllers.append(
            KeyboardController(player1)
        )

    if joystick.get_count() > 1:
        print("2-player game")
        player1.knight.pos.x *= 0.5
        player2 = KnightController(world.spawn_pc(color=(0.4, 0.9, 1.1, 1)))
        player2.knight.pos.x += player1.pos.x
        controllers.append(
            JoyController(player2, joystick.Joystick(1))
        )
    else:
        print("1-player game")

    clock.each_tick(update_input)


def update_input(dt):
    for controller in controllers:
        controller.update()


def create_world(scene):
    world = World(scene)
    clock.each_tick(world.update)
    return world

class Game:
    def __init__(self, settings):
        self.scene = None
        self.world = None
        self.time = 0.0
        self.frame = 0
        self.paused = False
        self.settings = settings

    def create_scene(self):
        print("[INFO] Creating scene...")
        self.scene = scene = Scene(
            1024,
            768,
            title="Ascend",
            rootdir=Path(ascend.__file__).parent
        )

        scene.background = (0.2, 0.2, 0.2)
        scene.layers[Layers.WALL_LAYER].set_effect(
            'dropshadow',
            radius=2,
            offset=(1.5, 1.5)
        )
        scene.layers[Layers.WALL_LAYER].set_effect(
            'dropshadow',
            radius=3,
            offset=(3, 3)
        )
        scene.layers[Layers.LOWER_EFFECTS_LAYER].set_effect(
            'bloom',
            radius=10,
        )

        smoke = scene.layers[Layers.LOWER_EFFECTS_LAYER].add_particle_group(
            texture='smoke',
            grow=0.1,
            max_age=0.8,
            drag=0.1,
        )
        smoke.add_color_stop(0, '#888888ff')
        smoke.add_color_stop(0.6, '#888888ff')
        smoke.add_color_stop(0.8, '#88888800')
        scene.smoke = smoke

        sparks = scene.layers[Layers.UPPER_EFFECTS_LAYER].add_particle_group(
            texture='spark',
            grow=0.1,
            max_age=0.6,
            drag=0.7,
        )
        sparks.add_color_stop(0, (2, 2, 0.8, 1))
        sparks.add_color_stop(0.3, (2, 1, 0, 1))
        sparks.add_color_stop(0.6, (0, 0, 0, 0))
        scene.sparks = sparks

        scene.bones = scene.layers[Layers.DEBRIS_LAYER].add_particle_group(
            texture='bone',
            max_age=4,
            drag=0.1,
            spin_drag=0.4,
        )
        scene.skulls = scene.layers[Layers.DEBRIS_LAYER].add_particle_group(
            texture='skull',
            max_age=4,
            drag=0.1,
            spin_drag=0.4,
        )
        for pgroup in (scene.bones, scene.skulls):
            pgroup.add_color_stop(0, '#bbbbbbff')
            pgroup.add_color_stop(1, '#bbbbbbff')
            pgroup.add_color_stop(4, '#bbbbbb00')


    def create_world(self):
        self.world = World(self)
        clock.each_tick(self.world.update)
        return self.world



    def new_game(self):
        self.paused = False

        self.world.new_game()

    def close_game(self):
        self.world.close_game()


    def update(self, dt, keyboard):
        self.time += dt
        self.frame += 1
