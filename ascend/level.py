import numpy as np
import math
import sys
import random
import json
import pkgutil
from itertools import product
from pygame import Rect

from wasabi2d import Vector2
from pygame import joystick

from .knight import Knight, Bomb, Player
from .mobs import Skeleton, Mage

from .vector2d import Vector2D, Polar2D
from .wall import Wall
from .mobs import Shooter, Stalker, Splitter, Blob
from .knight import KnightController
from .control import JoyController, KeyboardController

from . import control
from .constants import Layers, CollisionType


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


class Level:
    def __init__(self, game, gametype):
        self.game = game
        self.scene = game.scene

        self.pcs = []
        self.objects = []

        if gametype == "dan":
            self.mobs = []
            self.controllers = []
            self.update = self.dan_update
            self.dan_new_level()
        else:
            self.player = None
            self.enemies = []
            self.walls = []
            self.update = self.larry_update
            self.larry_new_level()

    def dan_new_level(self):
        self.create_players()
        self.spawn_mobs(num=20)

    def create_players(self):
        level = self
        player1 = KnightController(level.spawn_pc())

        if joystick.get_count() > 0:
            self.controllers.append(
                JoyController(player1, joystick.Joystick(0))
            )
        else:
            self.controllers.append(
                KeyboardController(player1.update)
            )
        self.controllers.append(player1)

        if joystick.get_count() > 1:
            print("2-player game")
            player1.knight.pos.x *= 0.5
            player2 = KnightController(level.spawn_pc(color=(0.4, 0.9, 1.1, 1)))
            player2.knight.pos.x += player1.pos.x
            self.controllers.append(
                JoyController(player2, joystick.Joystick(1))
            )
            self.controllers.append(player2)
        else:
            print("1-player game")

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

    def dan_update(self, t, dt, keyboard):
        for controller in self.controllers:
            controller.update(dt)

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
        player = self.player
        for mob in self.enemies[:]:
            collision = player.compute_collision_with_bad_guy(mob)

            if collision == CollisionType.ZONE:
                player.on_collision_zone(mob)
                mob.on_collide_zone()
            elif collision == CollisionType.PLAYER:
                player.on_collision_body(mob)
                mob.on_collide_player()
            else:
                penetration_vector = self.detect_wall_collisions(mob)
                if penetration_vector:
                    if mob.die_on_any_collision:
                        mob.close()
                        return
                    mob.pos -= penetration_vector
                    mob.shape.pos = mob.pos

        for i, mob1 in enumerate(self.enemies):
            p1 = mob1.pos
            r1 = mob1.radius
            for mob2 in self.enemies[i + 1:]:
                r2 = mob2.radius
                r = r1 + r2
                p2 = mob2.pos
                sep = Vector2(*p2 - p1)
                if sep.magnitude_squared() < r * r:
                    mag = sep.magnitude()
                    overlap = r - mag
                    if mag:
                        sep.normalize_ip()
                    else:
                        sep = Vector2(0, 1)
                    frac = (r1 * r1) / (r1 * r1 + r2 * r2)
                    mob1.pos = p1 - sep * overlap * (1.0 - frac)
                    mob2.pos = p2 + sep * overlap * frac

    def build_spatial_hash(self):
        self.wall_hash = {}
        for w in self.walls:
            for k in self.hash_coords(w.r):
                self.wall_hash.setdefault(k, []).append(w)

    HASH_SCALE = 80

    def hash_coords(self, rect):
        """Get an iterable of spatial hash keys."""
        s = self.HASH_SCALE
        l = rect.left // s
        r = rect.right // s + 1
        t = rect.top // s
        b = rect.bottom // s + 1
        return product(range(l, r), range(t, b))

    def detect_wall_collisions(self, entity):
        w = entity.radius * 2
        r = Rect(*entity.pos, w, w)
        hit_walls = set()
        for k in self.hash_coords(r):
            ws = self.wall_hash.get(k)
            if ws:
                hit_walls.update(ws)
        if not hit_walls:
            return None

        collisions = []
        for wall in hit_walls:
            collision = wall.collide_with_entity(entity)
            if collision:
                collisions.append(collision)

        if not collisions:
            return None
        if len(collisions) == 1:
            return collisions[0]

        cumulative_vector = collisions[0]
        for collision in collisions[1:]:
            cumulative_vector += collision
        return cumulative_vector

    def new_player(self):
        self.player = Player(self)
        self.pcs.append(self.player)

    def larry_update(self, t, dt, keyboard):
        if not self.player:
            return

        self.player.update(dt, keyboard)

        if not self.enemies:
            self.player.on_win()
        else:
            # TODO: decide we allow enemies to overlap
            self.resolve_collisions()
            for enemy in self.enemies:
                enemy.update(dt)

    def larry_new_level(self):
        print("[INFO] Spawning player and enemies...")

        scene = self.scene

        self.new_player()

        enemies = self.enemies
        walls = self.walls

        assert not (enemies or walls)

        generate_level(self)

        if len(sys.argv) > 1 and sys.argv[1] == "1":
            enemies.append(Blob(self))
        else:
            for i in range(15):
                enemies.append(Stalker(self, fast=False))

            for i in range(3):
                enemies.append(Stalker(self, fast=True))

            for i in range(2):
                enemies.append(Splitter(self))

            for i in range(5):
                enemies.append(Shooter(self))

        print("[INFO] Fight!")

    def delete(self):
        self.player.close()
        self.player = None
        self.pcs = []

        for enemy in self.enemies:
            enemy._close()
        self.enemies.clear()

        for wall in self.walls:
            wall._close()
        self.walls.clear()


# Components
ENDS = 3
MIDS = 3


def generate_level(level):
    left = random.randrange(ENDS) + 1
    mid = random.randrange(MIDS) + 1
    right = random.randrange(ENDS) + 1

    scene = level.scene

    l = 17
    t = 34
    sprites = [
        (f'bg-end-{left}', (l + 165, 350 + t), 0),
        (f'bg-mid-{mid}', (l + 165 + 330, 350 + t), 0),
        (f'bg-end-{right}', (l + 165 + 660, 350 + t), math.pi),
    ]
    for name, pos, rotation in sprites:
        w = scene.layers[Layers.ENTITIES].add_sprite(f'{name}-wall', pos=pos)
        w.angle = rotation
        w = scene.layers[Layers.FLOOR].add_sprite(f'{name}-floor', pos=pos)
        w.angle = rotation

    scene.background = '#2c332d'

    walls = level.walls

    for fname, pos, rotation in sprites:
        data = pkgutil.get_data(__name__, f'walldata/{fname}-walls.json')
        pts = json.loads(data.decode('ascii'))

        pos = Vector2D(pos)
        for loop in pts:
            poly = [pos + Vector2D(x - 165, y - 350).rotated(rotation) for x, y in loop]
            walls.append(Wall(level, poly, visible=False))


    scene.layers[Layers.FLOOR].add_sprite('trapdoor', pos=sprites[0][1])
    scene.layers[Layers.FLOOR].add_sprite('stairs', pos=sprites[2][1])
    level.build_spatial_hash()
