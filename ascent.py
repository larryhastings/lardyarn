from dataclasses import dataclass
import numpy as np
import math
from wasabi2d import Scene, event, run, Vector2, keyboard
from pygame import joystick
from knight import Knight


scene = Scene(title="Ascent - PyWeek 28")
scene.layers[0].set_effect('bloom', radius=10)

smoke = scene.layers[-1].add_particle_group(
    texture='smoke',
    grow=0.2,
    max_age=1.3,
)
smoke.add_color_stop(0, '#888888ff')
smoke.add_color_stop(0.6, '#888888ff')
smoke.add_color_stop(1.3, '#88888800')
scene.smoke = smoke


joystick.init()



knight = Knight(scene)


@dataclass
class JoyController:
    pc: Knight
    stick: joystick.Joystick

    def __post_init__(self):
        self.stick.init()

    def update(self):
        self.pc.accelerate((
            self.stick.get_axis(0),
            self.stick.get_axis(1),
        ))


@dataclass
class KeyboardController:
    pc: Knight

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

        knight.accelerate((ax, ay))


if joystick.get_count() > 0:
    controller = JoyController(knight, joystick.Joystick(0))
else:
    controller = KeyboardController(knight)


@event
def update(dt, keyboard):
    controller.update()
    knight.update(dt)


run()
