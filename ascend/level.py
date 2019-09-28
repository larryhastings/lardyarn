import numpy as np
import math
import sys

from wasabi2d import Vector2
from pygame import joystick

from .knight import Knight, Bomb, Player
from .mobs import Skeleton, Mage

from .vector2d import Vector2D, Polar2D
from .wall import Wall
from .mobs import Shooter, Stalker
from .knight import KnightController
from .control import JoyController, KeyboardController

from . import control
from .constants import Layers

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
                KeyboardController(player1)
            )

        if joystick.get_count() > 1:
            print("2-player game")
            player1.knight.pos.x *= 0.5
            player2 = KnightController(level.spawn_pc(color=(0.4, 0.9, 1.1, 1)))
            player2.knight.pos.x += player1.pos.x
            self.controllers.append(
                JoyController(player2, joystick.Joystick(1))
            )
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
            controller.update()

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

    def detect_wall_collisions(self, entity):
        collisions = []
        for wall in self.walls:
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
            for enemy in self.enemies:
                enemy.update(dt)

    def larry_new_level(self):
        print("[INFO] Spawning player and enemies...")

        scene = self.scene

        self.new_player()

        enemies = self.enemies
        walls = self.walls

        assert not (enemies or walls)

        ul = Vector2D(0, 0)
        lr = Vector2D(scene.width, scene.height)

        walls.append(Wall(self, ul, Vector2D(scene.width, 20)))
        walls.append(Wall(self, Vector2D(0, scene.height - 20), lr))

        walls.append(Wall(self, ul, Vector2D(20, scene.height)))
        walls.append(Wall(self, Vector2D(scene.width - 20, 0), lr))

        # and a wall in the middle to play with
        walls.append(Wall(self, Vector2D(600, 200), Vector2D(800, 400)))


        if len(sys.argv) > 1 and sys.argv[1] == "1":
            enemies.append(Stalker(self, fast=False))
        else:
            for i in range(15):
                enemies.append(Stalker(self, fast=False))

            for i in range(3):
                enemies.append(Stalker(self, fast=True))

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

        # clear out all layers
        for layer in dir(Layers):
            if layer.startswith("_"):
                continue
            value = getattr(Layers, layer)
            self.scene.layers[value].clear()
