from dataclasses import dataclass
import math

import numpy as np
from wasabi2d import Scene, event, run, keys
from wasabi2d.keyboard import keyboard
import pygame
from pygame import joystick

from knight import Knight
from world import World


scene = Scene(title="Ascent - PyWeek 28")
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

bones = scene.layers[-1].add_particle_group(
    texture='bone',
    max_age=4,
    drag=0.1,
    spin_drag=0.4,
)
skulls = scene.layers[-1].add_particle_group(
    texture='skull',
    max_age=4,
    drag=0.1,
    spin_drag=0.4,
)
for pgroup in (bones, skulls):
    pgroup.add_color_stop(0, '#bbbbbbff')
    pgroup.add_color_stop(1, '#bbbbbbff')
    pgroup.add_color_stop(4, '#bbbbbb00')


joystick.init()


@dataclass
class JoyController:
    pc: Knight
    stick: joystick.Joystick

    # buttons to map into what inputs
    BUTTON_MAP = [5, 1, 0, 2]

    def __post_init__(self):
        self.stick.init()
        self.buttons = range(self.stick.get_numbuttons())

    def update(self):
        self.pc.accelerate((
            self.stick.get_axis(0),
            self.stick.get_axis(1),
        ))
        inputs = tuple(self.stick.get_button(k) for k in self.BUTTON_MAP)
        self.pc.set_inputs(inputs)


@dataclass
class KeyboardController:
    pc: Knight

    KEY_MAP = [keys.Z, keys.X, keys.C, keys.V]

    def update(self):
        ax = ay = 0
        if keyboard.left:
            ax = -1
        elif keyboard.right:
            ax = 1

        if keyboard.up:
            ay = -1
        elif keyboard.down:
            ay = 1

        self.pc.accelerate((ax, ay))
        inputs = tuple(keyboard[k] for k in self.KEY_MAP)
        self.pc.set_inputs(inputs)


assert len(KeyboardController.KEY_MAP) == len(JoyController.BUTTON_MAP), \
        "Mismatch on number of inputs for controller types."


world = World(scene)

player1 = world.spawn_pc()
controllers = []

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
    player1.pos.x *= 0.5
    player2 = world.spawn_pc(color=(0.4, 0.9, 1.1, 1))
    player2.pos.x += player1.pos.x
    controllers.append(
        JoyController(player2, joystick.Joystick(1))
    )
else:
    print("1-player game")

world.spawn_mobs(num=20)


@event
def update(dt, keyboard):
    for controller in controllers:
        controller.update()

    world.update(dt)


SHIFT = pygame.KMOD_LSHIFT | pygame.KMOD_RSHIFT


@event
def on_key_down(key, mod):
    if key == key.F12:
        if mod & SHIFT:
            scene.toggle_recording()
        else:
            scene.screenshot()


run()
