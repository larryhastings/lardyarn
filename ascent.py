from dataclasses import dataclass
import math
import random

import numpy as np
from wasabi2d import Scene, event, run, Vector2, keys, animate
from wasabi2d.keyboard import keyboard
import pygame
from pygame import joystick

from knight import Knight


scene = Scene(title="Ascent - PyWeek 28")
scene.layers[0].set_effect('bloom', radius=10)

smoke = scene.layers[-1].add_particle_group(
    texture='smoke',
    grow=0.1,
    max_age=0.8,
    drag=0.1,
)
smoke.add_color_stop(0, '#888888ff')
smoke.add_color_stop(0.6, '#888888ff')
smoke.add_color_stop(0.8, '#88888800')
scene.smoke = smoke


joystick.init()



class Skeleton:
    def __init__(self, scene, pos, angle=0):
        self.scene = scene

        self.body = scene.layers[0].add_sprite(
            'skeleton-body',
            pos=pos,
            angle=angle
        )
        self.body_animate = None
        self.head = scene.layers[0].add_sprite(
            'skeleton-head',
            pos=pos,
            angle=angle
        )

        self.target = random.choice(pcs)
        self.bob = 1.0
        self.gait_speed = random.uniform(0.3, 0.5)
        self.gait_step = random.uniform(1.07, 1.2)

    SPEED = 30

    @property
    def pos(self):
        return Vector2(*self.head.pos)

    @pos.setter
    def pos(self, v):
        self.head.pos = self.body.pos = v

    def update(self, dt):
        to_target = Vector2(*self.target.pos - self.head.pos)
        dist, angle_deg = to_target.as_polar()
        angle_to_target = math.radians(angle_deg)
        self.head.angle = angle_to_target

        if dist > 30:
            self.head.pos += to_target.normalize() * self.SPEED * dt
            self.body.pos = self.head.pos
            self.bob += self.gait_speed * dt
            if self.bob > self.gait_step:
                self.bob = 1.0
            self.head.scale = self.bob
            self.body.scale = 1 + 0.5 * (self.bob - 1.0)

        self.body_animate = animate(
            self.body, duration=0.3, angle=angle_to_target
        )

    def delete(self):
        self.head.delete()
        self.body.delete()
        if self.body_animate:
            self.body_animate.stop()


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


mobs = []

def spawn_mobs(num):
    xs = np.random.uniform(30, scene.width - 30, size=num)
    ys = np.random.uniform(30, scene.height - 30, size=num)
    angles = np.random.uniform(-math.pi, math.pi, size=num)
    for x, y, angle in zip(xs, ys, angles):
        mobs.append(
            Skeleton(scene, Vector2(x, y), angle)
        )

spawn_mobs(20)


def line_segment_intersects_circle(start, along, center, radius):
    Q = center                  # Centre of circle
    r = radius                  # Radius of circle
    P1 = start      # Start of line segment
    V = along
    a = np.dot(V, V)
    b = 2 * np.dot(V, P1 - Q)
    c = np.dot(P1, P1) + np.dot(Q, Q) - 2 * np.dot(P1, Q) - r * r
    disc = b * b - 4 * a * c
    if disc < 0:
        return None
    sqrt_disc = math.sqrt(disc)
    t1 = (-b + sqrt_disc) / (2 * a)
    t2 = (-b - sqrt_disc) / (2 * a)
    if not (0 <= t1 <= 1 or 0 <= t2 <= 1):
        return None
    t = max(0, min(1, - b / (2 * a)))
    return P1 + t * V


@event
def update(dt, keyboard):
    for controller in controllers:
        controller.update()
    for pc in pcs:
        pc.update(dt)

    for pc in pcs:
        if not pc.sword.attack:
            continue

        pos = pc.pos
        sword = pc.sword.angle
        dir = Vector2(np.cos(sword), np.sin(sword))
        start = pos + dir * 12

        new_mobs = []
        for mob in mobs:
            if line_segment_intersects_circle(start, dir * 40, mob.pos, 20) is not None:
                mob.delete()
            else:
                new_mobs.append(mob)
        mobs[:] = new_mobs

    for mob in mobs:
        mob.update(dt)

    # Push actors apart. This is O(n^2)
    actors = pcs + mobs
    for i, mob1 in enumerate(actors):
        p1 = mob1.pos
        for mob2 in actors[i + 1:]:
            p2 = mob2.pos
            sep = Vector2(*p2 - p1)
            if sep.magnitude_squared() < 625:
                sep.normalize_ip()
                mob1.pos = p1 - sep
                mob2.pos = p2 + sep



SHIFT = pygame.KMOD_LSHIFT | pygame.KMOD_RSHIFT


@event
def on_key_down(key, mod):
    if key == key.F12:
        if mod & SHIFT:
            scene.toggle_recording()
        else:
            scene.screenshot()



run()
