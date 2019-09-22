from dataclasses import dataclass
import numpy as np
import math
from pygame import joystick
from wasabi2d import Scene, event, run, Vector2, keyboard


scene = Scene(title="Ascent - PyWeek 28")
scene.layers[0].set_effect('bloom', radius=10)

joystick.init()



class Knight:
    """The player character."""

    def __init__(self):
        self.shield = scene.layers[0].add_sprite('shield')
        self.sword = scene.layers[0].add_sprite('sword-gripped', angle=5)
        self.knight = scene.layers[0].add_sprite('knight')

        self.pos = Vector2(scene.width, scene.height) * 0.5
        self.v = Vector2()
        self.accel = Vector2()

        self.shield_angle = math.pi

    def accelerate(self, v):
        self.accel += Vector2(v)

    # Acceleration of the knight in pixels/s^2
    ACCELERATION = 600
    # Rate the knight is slowed, fraction of speed/s
    DRAG = 0.01

    def update(self, dt):
        """Update the knight this frame."""
        self.v *= self.DRAG ** dt   # drag

        if self.accel:
            # New acceleration this frame
            self.v += self.ACCELERATION * self.accel.normalize() * dt

        dv, angle = self.v.as_polar()
        if dv > 1e-2:
            self.knight.angle = math.radians(angle)

        self.pos += knight.v * dt
        self.knight.pos = self.pos
        self.sword.pos = self.pos + Vector2(60, -60)
        self._update_shield()
        self.accel *= 0.0

    @property
    def shield_angle(self):
        """Get the angle of the shield."""
        return self.shield.angle

    @shield_angle.setter
    def shield_angle(self, v):
        self.shield.angle = v
        self._update_shield()

    def _update_shield(self):
        v = self.shield.angle
        c = np.sin(v)
        s = np.cos(v)

        self.shield.pos = self.knight.pos + np.array([s, c]) * 40

    def delete(self):
        self.knight.delete()
        self.shield.delete()
        self.sword.delete()
        self.rhand.delete()



knight = Knight()


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
