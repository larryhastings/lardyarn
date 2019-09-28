import numpy as np
import math
import sys
import random
import json
import pkgutil
from itertools import product
from pygame import Rect

from wasabi2d import Vector2, animate, sounds
from pygame import joystick

from .knight import Knight, Bomb, Player
from .mobs import Skeleton, Mage

from .vector2d import Vector2D, Polar2D
from .wall import Wall
from .mobs import Shooter, Stalker, Splitter, Blob, Spawner, Prince
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
    def __init__(self, game, name):
        self.game = game
        self.scene = game.scene

        self.pcs = []
        self.objects = []

        self.player = None
        self.enemies = []
        self.shooters = set()
        self.walls = []
        self.update = self.larry_update
        self.name = name
        self.next = None
        self.proceed_on_button_release = False
        self.continue_level = False
        if name == "title screen":
            self.populate = self.title_screen

    def __repr__(self):
        return f"<Level {self.name!r}>"

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
                        mob.delete()
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

    HASH_SCALE = 30

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

    def delete_player(self):
        if self.player in self.pcs:
            self.pcs.remove(self.player)
        self.player.delete()
        self.player = None


    def larry_update(self, t, dt, keyboard):
        if not self.player:
            return

        if self.game.paused:
            # debounce button
            new_game_button_pressed = keyboard.space
            if not new_game_button_pressed and control.stick:
                new_game_button_pressed = control.stick.get_button(0)

            if new_game_button_pressed:
                self.proceed_on_button_release = True
            elif self.proceed_on_button_release:
                self.proceed_on_button_release = False
                if self.continue_level:
                    layers = self.scene.layers
                    for layer in (Layers.TEXT, Layers.TEXTBG):
                        layers[layer].clear()
                    self.delete_player()
                    self.new_player()
                    self.continue_level = False
                    self.game.paused = False
                else:
                    self.next_level()
            return

        if self.player:
            self.player.update(dt, keyboard)

        for o in self.objects[:]:
            o.update(dt)

        if not self.enemies:
            self.level_complete()
        else:
            # TODO: decide we allow enemies to overlap
            self.resolve_collisions()
            for enemy in self.enemies:
                enemy.update(dt)

    def populate(self):
        print("[INFO] Spawning player and enemies...")

        scene = self.scene

        self.new_player()
        self.objects.clear()

        enemies = self.enemies
        walls = self.walls
        assert not (enemies or walls)

        generate_level(self)

        class LevelSpawner:
            def __init__(self, level, *,
                slow_stalkers = 0,
                fast_stalkers = 0,
                splitters = 0,
                shooters = 0,
                spawners = 0,
                blobs = 0,
                princes = 0,
                next = None
                ):
                self.level = level
                self.slow_stalkers = slow_stalkers
                self.fast_stalkers = fast_stalkers
                self.splitters = splitters
                self.shooters = min(shooters, 10)
                self.spawners = spawners
                self.blobs = blobs
                self.princes = princes
                assert next
                self.next = next

            def spawn(self):
                enemies = self.level.enemies
                level = self.level

                for i in range(self.slow_stalkers):
                    enemies.append(Stalker(level, fast=False))

                for i in range(self.fast_stalkers):
                    enemies.append(Stalker(level, fast=True))

                for i in range(self.splitters):
                    enemies.append(Splitter(level))

                for i in range(self.shooters):
                    enemies.append(Shooter(level))

                assert self.spawners < 4
                if self.spawners:
                    width = self.level.scene.width
                    height = self.level.scene.height
                    corners = [
                        Vector2D(0, 0),
                        Vector2D(width, 0),
                        Vector2D(width, height),
                        Vector2D(0, height),
                        ]
                    random.shuffle(corners)
                    for i, corner in zip(range(self.spawners), corners):
                        enemies.append(Spawner(level, corner))

                for i in range(self.blobs):
                    enemies.append(Blob(level))

                if self.princes:
                    assert not enemies
                    scene = level.scene

                    three_quarters_across = Vector2D(scene.width * 3 / 4, scene.height / 2)
                    enemies.append(Prince(level, three_quarters_across))

                    scene.layers[Layers.TEXT].add_label(
                        text="You've found the prince!  Go to him!",
                        fontsize=48,
                        align="center",
                        pos=Vector2D(scene.width / 2, (scene.height * 3 / 4)),
                        font='magic_medieval',
                    )

                level.next = self.next

        if self.name.startswith("Endless "):
            level_number = int(self.name[8:])
            def n(base_n, max_n):
                return base_n + random.randint(base_n * level_number, max_n * level_number)
            spawner = LevelSpawner(self,
                    slow_stalkers=n(4, 6),
                    fast_stalkers=n(2, 3),
                    shooters=0 if level_number < 2 else n(0, 2),
                    blobs=0 if level_number < 3 else random.randint(0, 1),
                    spawners=0 if level_number < 5 else random.randint(0, 2),
                    next="Endless " + str(level_number + 1)
                    )
        else:
            level_spawners = {
                "1": LevelSpawner(self,
                    slow_stalkers=2,
                    # slow_stalkers=20,
                    # fast_stalkers=4,
                    next="5"
                    ),
                "2": LevelSpawner(self,
                    # slow_stalkers=30,
                    # shooters=5,
                    shooters=1,
                    next="3"
                    ),
                "3": LevelSpawner(self,
                    # slow_stalkers=30,
                    # shooters=5,
                    splitters=2,
                    next="4"
                    ),
                "4": LevelSpawner(self,
                    slow_stalkers=5,
                    fast_stalkers=1,
                    shooters=1,
                    splitters=2,
                    next="5"
                    ),
                "5": LevelSpawner(self,
                    blobs=1,
                    next="6"
                    ),
                "6": LevelSpawner(self,
                    slow_stalkers=10,
                    fast_stalkers=4,
                    splitters=5,
                    shooters=3,
                    spawners=2,
                    next="7"
                    ),
                "7": LevelSpawner(self,
                    princes=1,
                    next="title screen", # we won't get there
                    ),
            }
            spawner = level_spawners.get(self.name)
        assert spawner, "didn't have a spawner for level " + self.name
        spawner.spawn()

        print("[INFO] Fight!")

    def next_level(self):
        assert self.next
        next = Level(self.game, self.next)
        self.game.go_to_level(next)


    def show_message(self, text):
        scene = self.scene
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
        pos = screen_center - Vector2D(0, 1.3 * fontsize) * (lines - 0.5) * 0.5
        scene.layers[Layers.TEXT].add_label(
            text=text,
            fontsize=fontsize,
            align="center",
            pos=pos,
            font='magic_medieval',
        )

    def win(self):
        self.game.paused = True
        or_button_1 = "or button 1 " if control.stick else ""
        self.show_message(
            "YOU WIN!\n"
            f"Press Space {or_button_1}to continue\n"
        )
        sounds.game_won.play()

    def level_complete(self):
        self.game.paused = True
        or_button_1 = "or button 1 " if control.stick else ""
        self.show_message(
            "Level Complete\n"
            f"Press Space {or_button_1}to continue\n"
        )
        sounds.game_won.play()

    def lose(self, text):
        or_button_1 = "or button 1 " if control.stick else ""
        game = self.game
        if game.lives == 1:
            game_over = f"1 Life Remaining"
            self.continue_level = True
            game.lives = 0
        elif game.lives:
            game_over = f"{game.lives} Lives Remaining"
            self.continue_level = True
            game.lives -= 1
        else:
            game_over = f"GAME OVER\n"
            self.game.level.next = "title screen"
        self.show_message(
            f"{text}\n"
            f"{game_over}\n"
            f"Press Space {or_button_1}to continue\n"
            "Press Escape to quit"
        )
        sounds.hit.play()

    def title_screen(self):
        generate_level(self)
        or_button_1 = "or button 1 " if control.stick else ""
        or_button_4 = "or button 4 " if control.stick else ""
        self.show_message(
            f"Roller Knight\n"
            f"by Team Darn Yard Lad\n"
            "\n"
            f"Press Space {or_button_1}for New Game\n"
            f"Press 1 or {or_button_4}for an Endless Challenge\n"
            "Press Escape to... escape\n"
            "\n"
            "Copyright 2019 by Dan Pope & Larry Hastings\n"
            )
        self.update = self.title_screen_update
        self.populate = self.title_screen_populate

    def title_screen_populate(self):
        pass


    def title_screen_update(self, t, dt, keyboard):
        # debounce button
        endless_pressed = keyboard.k_1
        new_game_button_pressed = keyboard.space
        button_pressed = endless_pressed or new_game_button_pressed
        if not button_pressed and control.stick:
            endless_pressed = control.stick.get_button(3)
            new_game_button_pressed = control.stick.get_button(0)

        if new_game_button_pressed:
            self.proceed_on_button_release = "1"
        elif endless_pressed:
            self.proceed_on_button_release = "Endless 1"
        elif self.proceed_on_button_release:
            self.game.reset_game()
            level = Level(self.game, self.proceed_on_button_release)
            self.proceed_on_button_release = None
            self.game.go_to_level(level)

    def delete(self):
        if self.player:
            self.player.delete()
            self.player = None

        self.pcs = []

        for enemy in tuple(self.enemies):
            enemy.delete()
        assert not self.enemies

        for o in tuple(self.objects):
            o.delete()
        assert not self.objects

        for wall in tuple(self.walls):
            wall.delete()
        assert not self.walls


# Components
ENDS = 3
MIDS = 3


def generate_level(level, *, left=None, mid=None, right=None):
    if left is None:
        left = random.randrange(ENDS) + 1
    if mid is None:
        mid = random.randrange(MIDS) + 1
    if right is None:
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

