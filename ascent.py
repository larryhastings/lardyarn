from dataclasses import dataclass
import math

import numpy as np
from wasabi2d import Scene, event, run, Vector2, keys
from wasabi2d.keyboard import keyboard
import pygame
from pygame import joystick

from knight import Knight


scene = Scene(title="Ascent - PyWeek 28")
scene.layers[0].set_effect('bloom', radius=10)

smoke = scene.layers[-1].add_particle_group(
    texture='smoke',
    grow=0.2,
    max_age=1.3,
    drag=0.1,
)
smoke.add_color_stop(0, '#888888ff')
smoke.add_color_stop(0.6, '#888888ff')
smoke.add_color_stop(1.3, '#88888800')
scene.smoke = smoke


joystick.init()


@dataclass
class JoyController:
    pc: Knight
    stick: joystick.Joystick

    # buttons to map into what inputs
    BUTTON_MAP = [5, 1, 0]

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

    KEY_MAP = [keys.Z, keys.X, keys.C]

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


player1 = Knight(scene)
pcs = [player1]
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
    player2 = Knight(scene, color=(0.4, 0.9, 1.1, 1))
    player2.pos.x += player1.pos.x
    pcs.append(player2)
    controllers.append(
        JoyController(player2, joystick.Joystick(1))
    )
else:
    print("1-player game")


@event
def update(dt, keyboard):
    for controller in controllers:
        controller.update()
    for pc in pcs:
        pc.update(dt)


SHIFT = pygame.KMOD_LSHIFT | pygame.KMOD_RSHIFT


@event
def on_key_down(key, mod):
    if key == key.F12:
        if mod & SHIFT:
            scene.toggle_recording()
        else:
            scene.screenshot()



run()
