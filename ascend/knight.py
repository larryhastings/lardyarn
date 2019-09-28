import math
from typing import Any
from dataclasses import dataclass, field

import numpy as np
from wasabi2d import Vector2, animate, clock, sounds
from .vector2d import Vector2D, Polar2D, angle_diff, normalize_angle
from .collision import polygon_collision
from .constants import Layers, CollisionType

from . import control


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

    def __init__(self, level, pos, vel):
        self.level = level
        self.scene = level.scene
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
        self.level.objects.remove(self)
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
        for mob in self.level.mobs:
            sep = mob.pos - pos
            dmg = 1e5 / sep.magnitude_squared()
            if dmg > 30:
                mob.die(sep * 4)
            else:
                # TODO: apply impulse, rather than affecting position
                mob.pos += sep.normalize() * dmg
                survivors.append(mob)
        self.level.mobs[:] = survivors


class Knight:
    """The player character."""

    radius = 12

    def __init__(self, level, color=(1, 1, 1, 1)):
        self.level = level
        scene = self.scene = level.scene
        shield_sprite = scene.layers[Layers.ENTITIES].add_sprite('shield')
        sword_sprite = scene.layers[Layers.UPPER_EFFECTS].add_sprite('sword-gripped')
        sword_sprite.color = (1.4, 1.4, 1.4, 1)
        self.knight = scene.layers[Layers.ENTITIES].add_sprite('knight')
        self.head = scene.layers[Layers.ENTITIES].add_sprite('knight-head')

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
            angle=0,
        )
        self.sword.attack = False
        self.v = Vector2()

        self.pos = Vector2(scene.width, scene.height) * 0.5
        self.last_pos = None

        # The distance the knight has travelled; this is used in
        # calculating his gait
        self.step = 0

    @property
    def pos(self):
        return self.knight.pos

    @pos.setter
    def pos(self, v):
        self.head.pos = self.knight.pos = v
        self.shield.update()
        self.sword.update()

    @property
    def angle(self):
        return self.knight.angle

    @angle.setter
    def angle(self, v):
        self.knight.angle = v

    def update(self, dt):
        """Update the knight this frame."""

        if self.last_pos:
            displacement = Vector2(*self.pos - self.last_pos)
            distance = displacement.length()
            num = np.random.poisson(distance * self.SMOKE_RATE)
            if num:
                stern = self.pos - displacement.normalize() * 10
                self.scene.smoke.emit(
                    num=num,
                    pos=stern,
                    pos_spread=2,
                    vel=displacement * 0.3,
                    spin_spread=1,
                    size=7,
                    angle=self.knight.angle,
                    angle_spread=3,
                )

            self.step += distance

            # Scale the knight to simulate gait
            bob = 1.1 + 0.1 * np.sin(self.step / 500)
            self.knight.scale = self.head.scale = bob
        self.last_pos = Vector2(*self.pos)

    def throw_bomb(self):
        angle = self.knight.angle
        direction = Vector2()
        direction.from_polar((1, math.degrees(angle)))
        pos = Vector2(*self.knight.pos) + self.radius * direction
        vel = self.v + direction * Bomb.SPEED
        self.level.spawn_bomb(pos, vel)

    # Smoke in particles per pixel
    SMOKE_RATE = 0.07

    def delete(self):
        """Remove the knight from the scene."""
        self.head.delete()
        self.knight.delete()
        self.shield.delete()
        self.sword.delete()


@dataclass
class KnightController:
    knight: Knight

    can_act: Lockout = field(default_factory=Lockout)
    can_move: Lockout = field(default_factory=Lockout)

    # Acceleration of the knight in pixels/s^2
    ACCELERATION = 650
    # Rate the knight is slowed, fraction of speed/s
    DRAG = 0.2

    # Rate of turn, radians / s at full acceleration
    TURN = 10

    def __post_init__(self):
        self.v = Vector2()
        self.accel = Vector2()  # direction of the acceleration

        # clock.each_tick(self.update)

    @property
    def sword(self):
        return self.knight.sword

    @property
    def shield(self):
        return self.knight.shield

    def accelerate(self, v):
        if self.can_move:
            self.accel += Vector2(v)
            if self.accel.length_squared() > 1:
                self.accel.normalize_ip()
        else:
            v = Vector2(v)
            if self.v and v:
                side = self.v.normalize().rotate(90)
                self.accel += 0.3 * v * abs(side.dot(v.normalize()))

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

    def update(self, dt):
        self.v *= self.DRAG ** dt   # drag

        if self.accel:
            # New acceleration this frame
            self.v += self.ACCELERATION * self.accel * dt

        da, accel_angle = self.accel.as_polar()
        accel_angle = math.radians(accel_angle)

        delta = angle_diff(accel_angle, self.knight.angle)
        if delta < 0:
            self.knight.angle += max(dt * da * -self.TURN, delta)
        else:
            self.knight.angle += min(dt * da * self.TURN, delta)

        if da < 0.1:
            self.knight.head.angle = self.knight.angle
        else:
            self.knight.head.angle = accel_angle

        # Keep within the play area
        sz = Vector2(self.knight.radius, self.knight.radius)
        scene = self.knight.scene
        self.knight.pos = np.clip(
            self.knight.pos + self.v * dt,
            sz,
            Vector2(scene.width, scene.height) - sz
        )
        self.knight.v = self.v

        self.accel *= 0.0



# tweaked faster values
acceleration_scale = 1800
air_resistance = 0.07
max_speed = 700  # max observed speed is 691 anyway


max_speed_measured = 691.0


class Player:
    dead = False
    zone_angle = 0
    body_radius = 10
    # sword_radius = 25
    # radius = sword_radius
    # shield_arc = math.tau / 4 # how far the shield extends
    # zone_angle = 0
    zone_arc = math.tau / 4  # how far the shield extends
    zone_radius = 15
    outer_radius = body_radius + zone_radius
    radius = outer_radius
    # HACK: radius_squared is only used by collision with wall
    # and for that we ignore the zone and just use the body
    radius_squared = body_radius * body_radius

    # max speed measured: 590 and change
    zone_activation_speed = 350
    zone_grace_period = 0.1
    zone_grace_timeout = 0

    zone_center_distance = body_radius + (zone_radius / 2)
    zone_flash_until = 0

    message = None

    def __init__(self, level):
        self.level = level
        self.game = level.game
        scene = level.scene
        screen_center = Vector2D(scene.width / 2, scene.height / 2)
        self.pos = Vector2D(screen_center)
        self.shape = Knight(level)
        self.shape.knight.pos = self.pos

        self.momentum = Vector2D()

        # new "zone of destruction"
        self.normal_zone_color = (0.3, 0.3, 0.8)
        self.flashing_zone_color = (0.9, 0.9, 1)

        # draw zone as arc
        vertices = [Vector2D(self.body_radius, 0)]
        points_on_zone = 12
        # lame, range only handles ints. duh!
        start = -self.zone_arc / 2
        stop = self.zone_arc / 2
        step = (stop - start) / points_on_zone
        theta = start

        def append(theta):
            v = Vector2D(Polar2D(self.zone_radius, theta))
            v += Vector2D(self.body_radius, 0)
            vertices.append(tuple(v))
        while theta < stop:
            append(theta)
            theta += step

        self.zone_layer = scene.layers[Layers.ZONE]
        self.zone = self.zone_layer.add_polygon(
            vertices,
            fill=True,
            color=self.normal_zone_color
        )
        self.zone_center = self.pos + Vector2D(self.zone_center_distance, 0)
        self.zone_layer_active = False
        self.zone_layer.visible = False

        self.zone_triangle = self.previous_zone_triangle = []

    def show_message(self, text):
        scene = self.level.scene
        screen_center = Vector2D(scene.width, scene.height) * 0.5
        fill = scene.layers[Layers.TEXTBG].add_rect(
            width=scene.width + 100,
            height=scene.height + 100,
            pos=screen_center,
            color=(0, 0, 0, 0),
        )
        animate(fill, duration=0.1, color=(0, 0, 0, 0.33))

        lines = text.count('\n')
        fontsize = 48
        pos = screen_center - Vector2(0, 1.3 * fontsize) * (lines - 0.5) * 0.5
        scene.layers[Layers.TEXT].add_label(
            text=text,
            fontsize=fontsize,
            align="center",
            pos=pos,
            font='magic_medieval',
        )

    def close(self):
        self.shape.delete()
        self.zone.delete()
        for layer in (Layers.TEXT, Layers.TEXTBG):
            self.level.scene.layers[layer].clear()

    def compute_collision_with_bad_guy(self, bad_guy):
        if self.dead:
            return CollisionType.NONE

        distance_vector = self.pos - bad_guy.pos
        distance_squared = distance_vector.magnitude_squared
        intersect_outer_radius = distance_squared <= bad_guy.outer_collision_distance_squared
        if not intersect_outer_radius:
            return CollisionType.NONE

        # bad_guy intersecting with the zone?
        if self.zone_layer.visible:
            if (self.previous_zone_triangle
                and polygon_collision(self.previous_zone_triangle, bad_guy.pos, bad_guy.radius)):
                return CollisionType.ZONE

            if polygon_collision(self.zone_triangle, bad_guy.pos, bad_guy.radius):
                return CollisionType.ZONE

        intersect_body_radius = distance_squared <= bad_guy.body_collision_distance_squared
        # print(f"    interecting body? {intersect_body_radius}")

        if intersect_body_radius:
            return CollisionType.PLAYER

    def update(self, dt, keyboard):
        if self.zone_flash_until and (self.zone_flash_until < self.game.time):
            self.zone_flash_until = 0
            self.zone.color = self.normal_zone_color

        acceleration = Vector2D()
        for key, vector in control.movement_keys.items():
            if keyboard[key]:
                acceleration += vector

        if control.use_hat:
            x, y = control.stick.get_hat(0)
            if x or y:
                acceleration += Vector2D(x, -y)

        if control.use_left_stick:
            acceleration += Vector2D(
                control.stick.get_axis(0),
                control.stick.get_axis(1)
            )

        if acceleration.magnitude > 1.0:
            acceleration = acceleration.normalized()

        self.momentum = self.momentum * air_resistance ** dt + acceleration_scale * acceleration * dt
        if self.momentum.magnitude > max_speed:
            self.momentum = self.momentum.scaled(max_speed)

        # Rotate to face the direction of acceleration
        TURN = 12  # radians / s at full acceleration

        da, accel_angle = Polar2D(acceleration)
        delta = angle_diff(accel_angle, self.zone_angle)
        if delta < 0:
            self.zone_angle += max(dt * da * -TURN, delta)
        else:
            self.zone_angle += min(dt * da * TURN, delta)
        self.zone.angle = self.zone_angle = normalize_angle(self.zone_angle)

        starting_pos = self.pos
        movement_this_frame = self.momentum * dt
        self.pos += movement_this_frame
        if self.pos == starting_pos:
            return

        penetration_vector = self.level.detect_wall_collisions(self)
        if penetration_vector:
            # we hit one or more walls!

            # print(f"[{self.game.frame:6} {self.game.time:8}] collision! self.pos {self.pos} momentum {self.momentum} penetration_vector {penetration_vector}")
            self.pos -= penetration_vector

            # self.momentum = (-penetration_vector).scaled(self.momentum.magnitude)
            reflection_vector = Polar2D(penetration_vector)
            # print(f"  reflection_vector {reflection_vector}")
            # perpendicular to the bounce vector
            reflection_theta = reflection_vector.theta + math.pi / 2
            # print(f"  reflection_theta {reflection_theta}")
            current_momentum_theta = Polar2D(self.momentum).theta
            # print(f"current_momentum_theta {current_momentum_theta}")
            new_momentum_theta = (reflection_theta * 2) - current_momentum_theta
            # print(f"  new_momentum_theta {new_momentum_theta}")
            self.momentum = Vector2D(Polar2D(self.momentum.magnitude, new_momentum_theta))

            # print(f"[{self.game.frame:6} {self.game.time:8}] new self.pos {self.pos} momentum {self.momentum}")
            # print()

        self.zone.pos = self.shape.pos = self.pos

        current_speed = self.momentum.magnitude
        # global max_speed_measured
        # new_max = max(max_speed_measured, current_speed)
        # if new_max > max_speed_measured:
        #     max_speed_measured = new_max
        #     print("new max speed measured:", max_speed_measured)

        zone_currently_active = current_speed >= self.zone_activation_speed
        if zone_currently_active:
            if not self.zone_layer_active:
                # print("STATE 1: ZONE ACTIVE")
                self.zone_layer.visible = self.zone_layer_active = True
                self.zone_grace_timeout = 0
        else:
            if self.zone_layer_active:
                if not self.zone_grace_timeout:
                    # print("STATE 2: STARTING ZONE GRACE TIMEOUT")
                    self.zone_grace_timeout = self.game.time + self.zone_grace_period
                elif self.game.time < self.zone_grace_timeout:
                    pass
                else:
                    # print("STATE 3: ZONE TIMED OUT")
                    self.zone_grace_timeout = 0
                    self.zone_layer.visible = self.zone_layer_active = False

        if not self.zone_layer_active:
            self.previous_zone_triangle = self.zone_triangle = []
            return

        self.zone_center = self.pos + Polar2D(self.zone_center_distance, self.zone_angle)

        # cache zone triangle for collision detection purposes
        v1 = Vector2D(Polar2D(self.body_radius, self.zone_angle))
        v1 += self.pos
        v2delta = Vector2D(Polar2D(self.zone_radius, self.zone_angle - self.zone_arc / 2))
        v2 = v1 + v2delta
        v3delta = Vector2D(Polar2D(self.zone_radius, self.zone_angle + self.zone_arc / 2))
        v3 = v1 + v3delta
        self.previous_zone_triangle = self.zone_triangle
        self.zone_triangle = [v1, v2, v3]
        # print(f"player pos {self.pos} :: zone angle {self.zone_angle} triangle {self.zone_triangle}")
        self.shape.angle = self.zone_angle
        self.shape.update(dt)

    def on_collision_zone(self, other):
        """
        self and body are within sword radius.  are they colliding?
        Returns enum indicating type of collision.
        """
        self.zone_flash_until = self.game.time + 0.1
        self.zone.color = self.flashing_zone_color
        sounds.zap.play()

    def on_collision_body(self, other):
        """
        self and body are within body radius. they're colliding, but how?
        Returns enum indicating type of collision.
        """
        self.on_death(other)

    def on_death(self, other):
        print(f"[WARN] Player hit {other}!  Game over!")
        self.dead = True
        self.game.paused = True
        sounds.hit.play()
        # self.shape.delete()
        # self.shield.delete()

        self.show_message(
            "YOU DIED\n"
            "GAME OVER\n"
            "Press Space or joystick button to play again\n"
            "Press Escape to quit"
        )

    def on_win(self):
        global pause
        print("[INFO] Player wins!  Game over!")
        self.dead = True
        self.game.paused = True
        # sounds.hit.play()
        # self.shape.delete()
        # self.shield.delete()

        self.show_message(
            "A WINNER IS YOU!\n"
            "Press Space or joystick button to play again\n"
            "Press Escape to quit"
        )
        sounds.game_won.play()

