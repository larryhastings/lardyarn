import numpy as np
import math
from wasabi2d import Vector2

from knight import Knight, Bomb
from mobs import Skeleton, Mage


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


class World:
    def __init__(self, scene):
        self.scene = scene
        self.pcs = []
        self.objects = []
        self.mobs = []

    def spawn_pc(self, *, color='white') -> Knight:
        knight = Knight(self, color)
        self.pcs.append(knight)
        return knight

    def spawn_bomb(self, pos: Vector2, vel: Vector2) -> Bomb:
        bomb = Bomb(self, pos, vel)
        self.objects.append(bomb)
        return bomb

    def spawn_mobs(self, *, num: int):
        xs = np.random.uniform(30, self.scene.width - 30, size=num)
        ys = np.random.uniform(30, self.scene.height - 30, size=num)
        angles = np.random.uniform(-math.pi, math.pi, size=num)
        for x, y, angle in zip(xs, ys, angles):
            self.mobs.append(
                Mage(self, Vector2(x, y), angle)
            )

    def update(self, dt):
        for pc in self.pcs:
            pc.update(dt)

        for mob in self.mobs:
            mob.update(dt)

        for o in self.objects:
            o.update(dt)

        self.test_attacks()
        self.resolve_collisions()

    def test_attacks(self):
        for pc in self.pcs:
            if not pc.sword.attack:
                continue

            pos = pc.pos
            sword = pc.sword.angle
            dir = Vector2(np.cos(sword), np.sin(sword))
            start = pos + dir * 12

            new_mobs = []
            for mob in self.mobs:
                if line_segment_intersects_circle(start, dir * 40, mob.pos, 20) is not None:
                    sep = mob.pos - pc.pos
                    mob.die(pc.v + sep.normalize() * 30)
                else:
                    new_mobs.append(mob)
            self.mobs[:] = new_mobs

    def resolve_collisions(self):
        """Push actors apart. This is O(n^2) and can be improved.

        Note that this will not completely separate everything every frame
        due to a later collision causing a new intrusion on a previously
        resolved one. However over multiple frames this gives the desired
        effect.

        """
        actors = self.pcs + self.mobs
        for i, mob1 in enumerate(actors):
            p1 = mob1.pos
            r1 = mob1.radius
            for mob2 in actors[i + 1:]:
                r = r1 + mob2.radius
                p2 = mob2.pos
                sep = Vector2(*p2 - p1)
                if sep.magnitude_squared() < r * r:
                    mag = sep.magnitude()
                    overlap = r - mag
                    sep.normalize_ip()
                    mob1.pos = p1 - sep * overlap * 0.5
                    mob2.pos = p2 + sep * overlap * 0.5
