import math
import random
import numpy as np

from wasabi2d import Vector2, animate, clock


class MagicMissile:
    SMOKE_RATE = 20
    SPEED = 200
    SPIN = 0.5

    EXPLODE_TIME = 1
    BLINK_TIME = 2.3

    def __init__(self, world, pos, vel):
        self.world = world
        self.scene = world.scene
        self.vel = vel
        self.sprite = self.scene.layers[0].add_sprite(
            'spark',
            pos=pos,
        )
        self.sprite.color = (0.4, 3.0, 0.4, 1.0)
        self.sprite.scale = 0.3
        self.age = 0

    def update(self, dt):
        self.sprite.pos += self.vel * dt
        self.sprite.angle += self.SPIN * dt

        self.age += dt
        if self.age > self.EXPLODE_TIME:
            self.hit()
            return

        self.scene.smoke.emit(
            num=np.random.poisson(self.SMOKE_RATE * dt),
            pos=self.sprite.pos,
            vel_spread=10,
            spin_spread=1,
            size=6,
            size_spread=3,
            angle_spread=3,
            color=(0, 1, 0, 1.0),
        )
        self.scene.sparks.emit(
            num=np.random.poisson(self.SMOKE_RATE * dt),
            pos=self.sprite.pos,
            vel=self.vel * 0.8,
            vel_spread=30,
            spin_spread=1,
            size=4,
            angle_spread=3,
            color=(0.2, 1, 0.2, 1),
        )

    def delete(self):
        """Remove the missile from the world."""
        self.world.objects.remove(self)
        self.sprite.delete()

    def hit(self):
        """Kill the missile, showing an effect like it hit something."""
        pos = self.sprite.pos

        self.scene.smoke.emit(
            num=25,
            pos=pos,
            vel=-0.4 * self.vel,
            vel_spread=50,
            spin_spread=1,
            size=6,
            size_spread=3,
            angle_spread=3,
            color=(0, 2, 0, 1.0),
        )
        self.delete()


class Skeleton:
    radius = 12

    def __init__(self, world, pos, angle=0):
        self.world = world
        scene = self.scene = world.scene

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

    def die(self, vel=(0, 0)):
        self.delete()
        self.scene.bones.emit(
            10,
            pos=self.pos,
            vel=vel,
            vel_spread=80,
            spin_spread=3,
            size=6,
            size_spread=1,
            angle_spread=6,
        )
        self.scene.skulls.emit(
            1,
            pos=self.pos,
            vel=vel,
            vel_spread=80,
            spin_spread=1,
            size=8,
        )


class Mage(Skeleton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        clock.schedule(self.fire, random.randrange(30))

    def fire(self):
        """Fire a magic missile at the player."""
        pos = self.pos
        aim = Vector2(*self.target.pos) - pos

        self.world.objects.append(
            MagicMissile(self.world, pos, aim.normalize() * MagicMissile.SPEED)
        )
