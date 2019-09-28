from wasabi2d import Scene, event, run, clock
import pygame
from pygame import joystick

from .knight import KnightController
from .control import JoyController, KeyboardController
from .world import World


__all__ = [
    'run',
    'create_players',
]


def setup_scene(scene):
    scene.background = (0.2, 0.2, 0.2)
    scene.layers[0].set_effect(
        'dropshadow',
        radius=2,
        offset=(1.5, 1.5)
    )
    scene.layers[0].set_effect(
        'dropshadow',
        radius=3,
        offset=(3, 3)
    )
    scene.layers[1].set_effect(
        'bloom',
        radius=10,
    )

    smoke = scene.layers[0].add_particle_group(
        texture='smoke',
        grow=0.1,
        max_age=0.8,
        drag=0.1,
    )
    smoke.add_color_stop(0, '#888888ff')
    smoke.add_color_stop(0.6, '#888888ff')
    smoke.add_color_stop(0.8, '#88888800')
    scene.smoke = smoke

    sparks = scene.layers[1].add_particle_group(
        texture='spark',
        grow=0.1,
        max_age=0.6,
        drag=0.7,
    )
    sparks.add_color_stop(0, (2, 2, 0.8, 1))
    sparks.add_color_stop(0.3, (2, 1, 0, 1))
    sparks.add_color_stop(0.6, (0, 0, 0, 0))
    scene.sparks = sparks

    scene.bones = scene.layers[-1].add_particle_group(
        texture='bone',
        max_age=4,
        drag=0.1,
        spin_drag=0.4,
    )
    scene.skulls = scene.layers[-1].add_particle_group(
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

