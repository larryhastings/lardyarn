import math
from typing import Any
from dataclasses import dataclass, field

import numpy as np
from wasabi2d import Vector2, animate, clock


TAU = 2 * math.pi


def angle_diff(a, b):
    """Subtract angle b from angle a.

    Return the difference in the smallest direction.
    """
    diff = (a - b) % TAU
    return min(diff, diff - TAU, key=abs)


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
        k = self.knight.knight
        a = self.sprite.angle = k.angle + self._angle

        s = np.sin(a)
        c = np.cos(a)

        self.sprite.pos = k.pos + np.array([c, s]) * self.radius

    def delete(self):
        self.sprite.delete()


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


class Bomb:
    DRAG = 0.15
    SMOKE_RATE = 20
    SPEED = 200

    EXPLODE_TIME = 3
    BLINK_TIME = 2.3

    def __init__(self, world, pos, vel):
        self.world = world
        self.scene = world.scene
        self.vel = vel
        self.sprite = self.scene.layers[0].add_sprite('bomb', pos=pos)
        self.age = 0

    def update(self, dt):
        self.vel *= self.DRAG ** dt
        self.sprite.pos += self.vel * dt

        self.age += dt

        if self.age > self.EXPLODE_TIME:
            self.explode()
            return

        if self.age > self.BLINK_TIME:
            # We indicate the bomb is about to explode by making the
            # sparks stop ominously.
            return

        self.scene.sparks.emit(
            num=np.random.poisson(self.SMOKE_RATE * dt),
            pos=self.sprite.pos,
            vel_spread=30,
            spin_spread=1,
            size=3,
            angle_spread=3,
        )

    def explode(self):
        self.scene.camera.screen_shake()
        self.world.objects.remove(self)
        self.sprite.delete()
        self.pos = self.sprite.pos
        for pgroup in (self.scene.sparks,):
            pgroup.emit(
                num=100,
                pos=self.pos,
                vel_spread=200,
                spin_spread=1,
                size=8,
                angle_spread=3,
            )
        expl = self.scene.layers[1].add_sprite(
            'spark',
            pos=self.pos,
        )
        expl.scale = 0.1
        animate(
            expl,
            'accelerate',
            duration=0.3,
            scale=10,
            color=(1, 1, 1, 0),
            on_finished=expl.delete
        )
        self.apply_damage()

    def apply_damage(self):
        pos = Vector2(*self.pos)
        survivors = []
        for mob in self.world.mobs:
            sep = mob.pos - pos
            dmg = 1e5 / sep.magnitude_squared()
            if dmg > 30:
                mob.die(sep * 4)
            else:
                # TODO: apply impulse, rather than affecting position
                mob.pos += sep.normalize() * dmg
                survivors.append(mob)
        self.world.mobs[:] = survivors


class Knight:
    """The player character."""

    radius = 12

    def __init__(self, world, color=(1, 1, 1, 1)):
        self.world = world
        scene = self.scene = world.scene
        shield_sprite = scene.layers[0].add_sprite('shield')
        sword_sprite = scene.layers[1].add_sprite('sword-gripped')
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
        self.last_pos = None
        self.v = Vector2()
        self.accel = Vector2()  # direction of the acceleration

        # The distance the knight has travelled; this is used in
        # calculating his gait
        self.step = 0

    # Acceleration of the knight in pixels/s^2
    ACCELERATION = 650
    # Rate the knight is slowed, fraction of speed/s
    DRAG = 0.2

    # Rate of turn, radians / s at full acceleration
    TURN = 10

    @property
    def angle(self):
        return self.knight.angle

    @angle.setter
    def angle(self, v):
        self.knight.angle = v

    def update(self, dt):
        """Update the knight this frame."""
        self.v *= self.DRAG ** dt   # drag

        if self.accel:
            # New acceleration this frame
            self.v += self.ACCELERATION * self.accel * dt

        da, accel_angle = self.accel.as_polar()
        accel_angle = math.radians(accel_angle)

        dv = self.v.magnitude()

        delta = angle_diff(accel_angle, self.knight.angle)
        if delta < 0:
            self.knight.angle += max(dt * da * -self.TURN, delta)
        else:
            self.knight.angle += min(dt * da * self.TURN, delta)

        if da < 0.1:
            self.head.angle = self.knight.angle
        else:
            self.head.angle = accel_angle

        self.step += dv

        # Scale the knight to simulate gait
        bob = 1.1 + 0.1 * np.sin(self.step / 500)
        self.knight.scale = self.head.scale = bob

        # Keep within the play area
        sz = Vector2(self.radius, self.radius)
        self.pos = np.clip(
            self.pos + self.v * dt,
            sz,
            Vector2(self.scene.width, self.scene.height) - sz
        )

        self.head.pos = self.knight.pos = self.pos
        self.shield.update()
        self.sword.update()
        self.accel *= 0.0

        if self.last_pos:
            displacement = Vector2(*self.pos - self.last_pos)
            num = np.random.poisson(displacement.length() * self.SMOKE_RATE)
            if num:
                stern = self.pos - displacement.normalize() * 10
                self.scene.smoke.emit(
                    num=num,
                    pos=stern,
                    pos_spread=2,
                    vel=self.v * 0.3,
                    spin_spread=1,
                    size=7,
                    angle=self.knight.angle,
                    angle_spread=3,
                )
        self.last_pos = Vector2(*self.pos)

    def throw_bomb(self):
        angle = self.knight.angle
        direction = Vector2()
        direction.from_polar((1, math.degrees(angle)))
        pos = Vector2(*self.knight.pos) + self.radius * direction
        vel = self.v + direction * Bomb.SPEED
        self.world.spawn_bomb(pos, vel)

    # Smoke in particles per pixel
    SMOKE_RATE = 0.07

    def delete(self):
        """Remove the knight from the scene."""
        self.knight.delete()
        self.shield.delete()
        self.sword.delete()


@dataclass
class KnightController:
    knight: Knight

    can_act: Lockout = field(default_factory=Lockout)
    can_move: Lockout = field(default_factory=Lockout)

    @property
    def sword(self):
        return self.knight.sword

    @property
    def shield(self):
        return self.knight.shield

    def accelerate(self, v):
        if self.can_move:
            self.knight.accel += Vector2(v)
            if self.knight.accel.length_squared() > 1:
                self.knight.accel.normalize_ip()
        else:
            v = Vector2(v)
            if self.knight.v and v:
                side = self.knight.v.normalize().rotate(90)
                self.knight.accel += 0.3 * v * abs(side.dot(v.normalize()))

    def set_inputs(self, inputs):
        """Pass information from the controller."""

        defend, attack, charge, bomb = inputs

        if not self.can_act:
            return

        if defend:
            self.can_act.lock(0.3)
            animate(self.shield, duration=0.1, angle=-0.2, radius=8)
            animate(self.sword, duration=0.3, angle=1.3, radius=25)
        elif bomb:
            self.can_act.lock(0.5)
            self.knight.throw_bomb()
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
            on_finished=self._end_attack
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
        self.knight.accel = Vector2(c, s) * 2
        x, y = self.knight.pos
        radius = self.knight.radius
        scene = self.knight.scene
        if self.charge_t > 1.5 or \
                x < radius or x > scene.width - radius or \
                y < radius or y > scene.height - radius:
            clock.unschedule(self._charge)
            self.sword.attack = False
            self.can_act.unlock()
            self.can_move.unlock()

    def normal_stance(self):
        """Return the knight to his rest pose."""
        animate(self.shield, duration=0.3, angle=-1, radius=12)
        animate(self.sword, 'accel_decel', duration=0.3, angle=1, radius=25)
