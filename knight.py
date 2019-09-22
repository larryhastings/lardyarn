import math
from typing import Any
from dataclasses import dataclass

import numpy as np
from wasabi2d import Vector2, animate, clock


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

        s = np.sin(a)
        c = np.cos(a)

        self.sprite.pos = k.pos + np.array([c, s]) * self.radius


@dataclass
class Lockout:
    state: bool = True

    def lock(self, duration=0.1):
        """Disable attack for at least as long as duration."""
        self.state = False
        clock.schedule_unique(self._enable, duration)

    def unlock(self):
        self.state = True
        clock.unschedule(self._enable)

    def __bool__(self):
        return self.state

    def _enable(self):
        self.state = True



class Knight:
    """The player character."""

    def __init__(self, scene, color=(1, 1, 1, 1)):
        self.scene = scene
        shield_sprite = scene.layers[0].add_sprite('shield')
        sword_sprite = scene.layers[0].add_sprite('sword-gripped')
        sword_sprite.color = (1.4, 1.4, 1.4, 1)
        self.knight = scene.layers[0].add_sprite('knight')
        self.head = scene.layers[0].add_sprite('knight-head')

        for spr in (self.knight, self.head):
            spr.color = color

        self.shield = Hand(
            sprite=shield_sprite,
            knight=self,
            radius=12,
            angle=-1.5,
        )
        self.sword = Hand(
            sprite=sword_sprite,
            knight=self,
            radius=25,
            angle=1,
        )
        self.sword.attack = False

        self.pos = Vector2(scene.width, scene.height) * 0.5
        self.v = Vector2()
        self.accel = Vector2()  # direction of the acceleration

        # The distance the knight has travelled; this is used in
        # calculating his gait
        self.step = 0

        self.can_act = Lockout()
        self.can_move = Lockout()

    def accelerate(self, v):
        if self.can_move:
            self.accel += Vector2(v)
            if self.accel.length_squared() > 1:
                self.accel.normalize_ip()

    def set_inputs(self, inputs):
        """Pass information from the controller."""

        defend, attack, charge = inputs

        if not self.can_act:
            return

        if defend:
            self.can_act.lock(0.3)
            animate(self.shield, duration=0.1, angle=-0.2, radius=8)
            animate(self.sword, duration=0.3, angle=1.3, radius=25)
        elif charge:
            self.can_move.lock(1.8)
            self.can_act.lock(1.8)
            animate(self.shield, duration=0.1, angle=0, radius=10)
            animate(self.sword, duration=0.1, angle=0, radius=20)
            clock.schedule(self._start_charge, 0.3)
        elif attack:
            self.can_act.lock(0.5)
            animate(
                self.sword,
                'accel_decel',
                duration=0.05,
                angle=2.5,
                on_finished=self._start_attack
            )
        else:
            self.normal_stance()

    def _start_attack(self):
        """Initiate the attack."""
        self.sword.attack = True
        animate(self.shield, duration=0.08, angle=-1.3)
        animate(
            self.sword,
            duration=0.15,
            tween='accel_decel',
            angle=-1.5,
            radius=30,
            on_finished=self._end_attack()
        )

    def _end_attack(self):
        self.sword.attack = False
        self.normal_stance()

    def _start_charge(self):
        self.sword.attack = True
        clock.each_tick(self._charge)
        self.charge_t = 0

    def _charge(self, dt):
        self.charge_t += dt
        angle = self.knight.angle
        c, s = np.cos(angle), np.sin(angle)
        self.accel = Vector2(c, s) * 2
        x, y = self.knight.pos
        if self.charge_t > 1.5 or \
                x < 30 or x > self.scene.width - 30 or \
                y < 30 or y > self.scene.height - 30:
            clock.unschedule(self._charge)
            self.sword.attack = False
            self.can_act.unlock()
            self.can_move.unlock()

    def normal_stance(self):
        """Return the knight to his rest pose."""
        animate(self.shield, duration=0.3, angle=-1, radius=12)
        animate(self.sword, 'accel_decel', duration=0.3, angle=1, radius=25)

    # Acceleration of the knight in pixels/s^2
    ACCELERATION = 650
    # Rate the knight is slowed, fraction of speed/s
    DRAG = 0.01

    def update(self, dt):
        """Update the knight this frame."""
        self.v *= self.DRAG ** dt   # drag

        if self.accel:
            # New acceleration this frame
            self.v += self.ACCELERATION * self.accel * dt

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
        bob = 1.1 + 0.1 * np.sin(self.step / 500)
        self.knight.scale = self.head.scale = bob

        sz = Vector2(10, 10)
        self.pos = np.clip(
            self.pos + self.v * dt,
            sz,
            Vector2(self.scene.width, self.scene.height) - sz
        )

        self.head.pos = self.knight.pos = self.pos
        self.shield.update()
        self.sword.update()
        self.accel *= 0.0

        if dv > 1e-2:
            stern = self.pos - self.v.normalize() * 10
            self.scene.smoke.emit(
                num=np.random.poisson(self.v.length() * self.SMOKE_RATE * dt),
                pos=stern,
                pos_spread=2,
                vel=self.v * 0.3,
                spin_spread=1,
                size=7,
            )

    # Smoke in particles per pixel
    SMOKE_RATE = 0.07

    def delete(self):
        """Remove the knight from the scene."""
        self.knight.delete()
        self.shield.delete()
        self.sword.delete()
        self.rhand.delete()

