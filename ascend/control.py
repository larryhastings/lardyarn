from typing import Any
from dataclasses import dataclass

from wasabi2d import keys
from wasabi2d.keyboard import keyboard
from pygame import joystick

from .vector2d import Vector2D, Polar2D


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

    def update(self, dt):
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

    def update(self, dt):
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

movement_keys = {}
stick = None
use_left_stick = use_hat = False

def init_controls(settings):
    global movement_keys
    global stick
    global use_left_stick
    global use_hat

    movement_keys[keys.W] = movement_keys[keys.UP]    = Vector2D(+0, -1)
    movement_keys[keys.S] = movement_keys[keys.DOWN]  = Vector2D(+0, +1)
    movement_keys[keys.A] = movement_keys[keys.LEFT]  = Vector2D(-1, +0)
    movement_keys[keys.D] = movement_keys[keys.RIGHT] = Vector2D(+1, +0)

    which_joystick = settings['joystick']
    if which_joystick < joystick.get_count():
        stick = joystick.Joystick(which_joystick)
        stick.init()
        axes = stick.get_numaxes()
        noun = "axis" if axes == 1 else "axes"
        print(f"[INFO] {axes} joystick analogue {noun}")
        use_left_stick = (
            (max(settings['move x axis'], settings['move y axis']) < axes)
            and
            (min(settings['move x axis'], settings['move y axis']) >= 0))

        buttons = stick.get_numbuttons()
        noun = "button" if buttons == 1 else "buttons"
        print(f"[INFO] {buttons} joystick {noun}")

        hats = stick.get_numhats()
        noun = "hat" if hats == 1 else "hats"
        print(f"[INFO] {hats} joystick {noun}")
        use_hat = hats >= 1
        use_hat = (
            (settings['hat'] < hats)
            and
            (settings['hat'] >= 0))
    else:
        print(f"[WARN] Insufficient joysticks!")
        print(f"[WARN] We want joystick #{which_joystick}, but only {joystick.get_count()} joysticks detected.")
        use_left_stick = use_hat = False
        stick = None

    print("[INFO] use left stick?", use_left_stick)
    print("[INFO] use hat?", use_hat)
