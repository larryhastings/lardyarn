from typing import Any
from dataclasses import dataclass

from wasabi2d import keys
from wasabi2d.keyboard import keyboard
from pygame import joystick


joystick.init()


@dataclass
class JoyController:
    pc: Any
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
    pc: Any

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
