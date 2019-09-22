import math
from typing import Any

import numpy as np
from wasabi2d import Vector2, animate


TAU = 2 * math.pi


def angle_diff(a, b):
    """Find the difference between two angles in radians."""
    diff = abs(a - b) % TAU
    return min(diff, TAU - diff)



class Hand:
    """An object held in the knight's hand."""
    knight: 'Knight'
    sprite: Any
    _angle: float
    radius: float

    def __init__(self, knight, sprite, angle=0, radius=20):
        self.knight = knight
        self.sprite = sprite
        self.radius = radius
        self.angle = angle

    @property
    def angle(self):
        """Get the angle of the shield."""
        return self._angle

    @angle.setter
    def angle(self, v):
        """Set the angle of the shield, relative to the knight."""
        self._angle = v
        self.update()

    def update(self):
        v = self._angle
        k = self.knight.knight
        a = self.sprite.angle = k.angle + self._angle

        c = np.sin(a)
        s = np.cos(a)

        self.sprite.pos = k.pos + np.array([s, c]) * self.radius


class Knight:
    """The player character."""

    def __init__(self, scene):
        self.scene = scene
        shield_sprite = scene.layers[0].add_sprite('shield')
        self.sword = scene.layers[0].add_sprite('sword-gripped', angle=5)
        self.knight = scene.layers[0].add_sprite('knight')
        self.head = scene.layers[0].add_sprite('knight-head')

        self.shield = Hand(
            sprite=shield_sprite,
            knight=self,
            radius=40,
            angle=-1.5,
        )

        self.pos = Vector2(scene.width, scene.height) * 0.5
        self.v = Vector2()
        self.accel = Vector2()

        # The distance the knight has travelled; this is used in
        # calculating his gait
        self.step = 0

    def accelerate(self, v):
        self.accel += Vector2(v)

    def set_inputs(self, inputs):
        """Pass information from the controller."""
        defend, = inputs
        if defend:
            animate(self.shield, duration=0.1, angle=-0.2, radius=25)
        else:
            animate(self.shield, duration=0.1, angle=-1.5, radius=40)

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
            animate(self.knight, duration=0.1, angle=math.radians(angle))

        da, accel_angle = self.accel.as_polar()
        if da < 0.1:
            look = self.knight.angle
        else:
            look = math.radians(accel_angle)

        animate(self.head, duration=0.1, angle=look)

        self.step += dv

        # Scale the knight to simulate gait
        bob = 1.05 + 0.05 * np.sin(self.step / 300)
        self.knight.scale = self.head.scale = bob

        self.pos += self.v * dt
        self.head.pos = self.knight.pos = self.pos
        self.sword.pos = self.pos + Vector2(60, -60)
        self.shield.update()
        self.accel *= 0.0

        if dv > 1e-2:
            stern = self.pos - self.v.normalize() * 10
            self.scene.smoke.emit(
                num=np.random.poisson(self.v.length() * self.SMOKE_RATE * dt),
                pos=stern,
                pos_spread=4,
                spin_spread=1,
                size=20,
            )

    # Smoke in particles per pixel
    SMOKE_RATE = 0.03

    def delete(self):
        """Remove the knight from the scene."""
        self.knight.delete()
        self.shield.delete()
        self.sword.delete()
        self.rhand.delete()

