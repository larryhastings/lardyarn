import math
import random

import numpy as np
from wasabi2d import Vector2, animate


class Skeleton:
    radius = 12

    def __init__(self, world, pos, angle=0):
        self.world = world
        scene = world.scene

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

        self.target = random.choice(world.pcs)
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

