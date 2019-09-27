#!/usr/bin/env python3

print("[INFO] Importing packages...")


import enum
import sys
import math
import random
import os.path


if hasattr(os, "getwindowsversion"):
    rcfile_basename = "lardyarn.txt"
else:
    rcfile_basename = ".lardyarnrc"

rcfile_schema = {
    'mixer devicename': (None, str),
    'joystick': 0,
    'hat': 0,
    'move x axis': 0,
    'move y axis': 1,
}

settings = {}
for name, value in rcfile_schema.items():
    if isinstance(value, tuple):
        value, _ = value
    settings[name] = value


rcfile_path = os.path.expanduser("~/" + rcfile_basename)
if os.path.isfile(rcfile_path):
    with open(rcfile_path, "rt") as f:
        for line in f.read().strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            name, equals, value = line.partition("=")
            if not equals:
                sys.exit("Invalid rcfile line: " + repr(line))
            name = name.strip()
            value = value.strip()
            default = rcfile_schema.get(name)
            if default is None:
                sys.exit("Invalid value specified in rcfile: " + repr(name))
            if isinstance(default, tuple):
                default, defaulttype = default
            else:
                defaulttype = type(default)
            settings[name] = defaulttype(value)


stdout = sys.stdout
sys.stdout = None
import pygame
sys.stdout = stdout

print("[INFO] Initializing sound...")

devicename=settings.get('mixer devicename')
pygame.mixer.pre_init(devicename=devicename)
pygame.init()
try:
    pygame.mixer.init()
except pygame.error as e:
    print("[WARN] Couldn't get exclusive access to sound device!  Sound disabled.")
    print("[WARN]", e)
    # call pre-init again with no devicename
    # this will reset back to the default
    # which ALSO won't work, but pygame works better this way
    pygame.mixer.pre_init(devicename=None)
    pygame.mixer.init()

print("[INFO] Finishing imports...")

import wasabi2d
from wasabi2d import Scene, run, event, clock, keys, sounds
import pygame.mouse
from pygame import joystick
from triangle_intersect import polygon_collision
from vector2d import Vector2D, Polar2D


print("[INFO] Initializing runtime...")

class CollisionType(enum.IntEnum):
    NO_COLLISION = 0
    COLLISION_WITH_WALL = 1
    COLLISION_WITH_PLAYER = 2
    COLLISION_WITH_ZONE = 3

class Layers(enum.IntEnum):
    WALL_LAYER = 0
    ENTITIES_LAYER = 1
    BULLETS_LAYER = 2
    ZONE_LAYER = 3
    TEXT_LAYER = 4



def angle_diff(a, b):
    """Subtract angle b from angle a.

    Return the difference in the smallest direction.
    """
    diff = (a - b) % math.tau
    return min(diff, diff - math.tau, key=abs)


def normalize_angle(theta):
    if theta > math.pi:
        theta -= math.tau
    elif theta < -math.pi:
        theta += math.tau
    return theta


max_speed_measured = 691.0

class Player:
    dead = False
    zone_angle = 0
    body_radius = 10
    # sword_radius = 25
    # radius = sword_radius
    # shield_arc = math.tau / 4 # how far the shield extends
    # zone_angle = 0
    zone_arc = math.tau / 4 # how far the shield extends
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

    def __init__(self):
        self.pos = Vector2D(screen_center)
        self.shape = scene.layers[Layers.ENTITIES_LAYER].add_circle(
            radius=self.body_radius,
            pos=self.pos,
            color=(0, 1/2, 0),
            )

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

        self.zone_layer = scene.layers[Layers.ZONE_LAYER]
        self.zone = self.zone_layer.add_polygon(vertices, fill=True, color=self.normal_zone_color)
        self.zone_center = self.pos + Vector2D(self.zone_center_distance, 0)
        self.zone_layer_active = False
        self.zone_layer.visible = False

        self.message = scene.layers[Layers.TEXT_LAYER].add_label(
            text = ".",
            fontsize = 44.0,
            align = "center",
            pos = screen_center,
            )
        self.message.text = ""

    def close(self):
        self.shape.delete()
        self.zone.delete()
        if self.message:
            # del self.message
            # self.message.delete()
            self.message.text = ""

    def compute_collision_with_bad_guy(self, bad_guy):
        if self.dead:
            return CollisionType.NO_COLLISION

        distance_vector     = self.pos - bad_guy.pos
        distance_squared = distance_vector.magnitude_squared
        intersect_outer_radius = distance_squared <= bad_guy.outer_collision_distance_squared
        if not intersect_outer_radius:
            return CollisionType.NO_COLLISION

        # bad_guy intersecting with the zone?
        if self.zone_layer.visible:
            if polygon_collision(self.zone_triangle, bad_guy.pos, bad_guy.radius):
                return CollisionType.COLLISION_WITH_ZONE

        intersect_body_radius = distance_squared <= bad_guy.body_collision_distance_squared
        # print(f"    interecting body? {intersect_body_radius}")

        if intersect_body_radius:
            return CollisionType.COLLISION_WITH_PLAYER

    def update(self, dt, keyboard):
        if self.zone_flash_until and (self.zone_flash_until < time):
            self.zone_flash_until = 0
            self.zone.color = self.normal_zone_color

        acceleration = Vector2D()
        for key, vector in movement_keys.items():
            if keyboard[key]:
                acceleration += vector

        if use_hat:
            x, y = stick.get_hat(0)
            if x or y:
                acceleration += Vector2D(x, -y)

        if use_left_stick:
            acceleration += Vector2D(
                stick.get_axis(0),
                stick.get_axis(1)
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

        penetration_vector = detect_wall_collisions(self)
        if penetration_vector:
            # we hit one or more walls!

            # print(f"[{frame:6} {time:8}] collision! self.pos {self.pos} momentum {self.momentum} penetration_vector {penetration_vector}")
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

            # print(f"[{frame:6} {time:8}] new self.pos {self.pos} momentum {self.momentum}")
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
                    self.zone_grace_timeout = time + self.zone_grace_period
                elif time < self.zone_grace_timeout:
                    pass
                else:
                    # print("STATE 3: ZONE TIMED OUT")
                    self.zone_grace_timeout = 0
                    self.zone_layer.visible = self.zone_layer_active = False

        self.zone_center = self.pos + Polar2D(self.zone_center_distance, self.zone_angle)

        # cache zone triangle for collision detection purposes
        v1 = Vector2D(Polar2D(self.body_radius, self.zone_angle))
        v1 += self.pos
        v2delta = Vector2D(Polar2D(self.zone_radius, self.zone_angle - self.zone_arc / 2))
        v2 = v1 + v2delta
        v3delta = Vector2D(Polar2D(self.zone_radius, self.zone_angle + self.zone_arc / 2))
        v3 = v1 + v3delta
        self.zone_triangle = [v1, v2, v3]
        # print(f"player pos {self.pos} :: zone angle {self.zone_angle} triangle {self.zone_triangle}")


    def on_collision_zone(self, other):
        """
        self and body are within sword radius.  are they colliding?
        Returns enum indicating type of collision.
        """
        self.zone_flash_until = time + 0.1
        self.zone.color = self.flashing_zone_color
        sounds.zap.play()


    def on_collision_body(self, other):
        """
        self and body are within body radius. they're colliding, but how?
        Returns enum indicating type of collision.
        """
        self.on_death(other)


    def on_death(self, other):
        global pause
        print(f"[WARN] Player hit {other}!  Game over!")
        self.dead = True
        pause = True
        sounds.hit.play()
        # self.shape.delete()
        # self.shield.delete()

        self.message.text = "YOU DIED\nGAME OVER\npress Space or joystick button to play again\npress Escape to quit"

    def on_win(self):
        global pause
        print("[INFO] Player wins!  Game over!")
        self.dead = True
        pause = True
        # sounds.hit.play()
        # self.shape.delete()
        # self.shield.delete()

        self.message.text = "A WINNER IS YOU!\ngame over\npress Space or joystick button to play again\npress Escape to quit"
        sounds.game_won.play()



movement_keys = {}
movement_keys[keys.W] = movement_keys[keys.UP]    = Vector2D(+0, -1)
movement_keys[keys.S] = movement_keys[keys.DOWN]  = Vector2D(+0, +1)
movement_keys[keys.A] = movement_keys[keys.LEFT]  = Vector2D(-1, +0)
movement_keys[keys.D] = movement_keys[keys.RIGHT] = Vector2D(+1, +0)


joystick.init()
which_joystick = settings['joystick']
if which_joystick < joystick.get_count():
    stick = joystick.Joystick(which_joystick)
    stick.init()
    axes = stick.get_numaxes()
    noun = "axis" if axes == 1 else "axes"
    print(f"[INFO] {axes} joystick analogue {noun}")
    use_left_stick = (
        (max(settings['move x axis'], settings['move y axis']) < axes)
        and
        (min(settings['move x axis'], settings['move y axis']) >= 0))

    buttons = stick.get_numbuttons()
    noun = "button" if buttons == 1 else "buttons"
    print(f"[INFO] {buttons} joystick {noun}")

    hats = stick.get_numhats()
    noun = "hat" if hats == 1 else "hats"
    print(f"[INFO] {hats} joystick {noun}")
    use_hat = hats >= 1
    use_hat = (
        (settings['hat'] < hats)
        and
        (settings['hat'] >= 0))
else:
    print(f"[WARN] Insufficient joysticks!")
    print(f"[WARN] We want joystick #{which_joystick}, but only {joystick.get_count()} joysticks detected.")
    use_left_stick = use_right_stick = use_face_buttons = use_hat = False
    stick = None

print("[INFO] use left stick?", use_left_stick)
print("[INFO] use hat?", use_hat)



# tweaked faster values
acceleration_scale = 1800
air_resistance = 0.07
max_speed = 700 # max observed speed is 691 anyway


time = 0
frame = 0

enemies = []
walls = []

@event
def update(dt, keyboard):
    global time
    global frame

    if keyboard.escape:
        sys.exit("[INFO] Quittin' time!")

    if pause:
        if stick:
            for button in (0, 1, 2, 3):
                if stick.get_button(button):
                    close_game()
                    new_game()
        return

    time += dt
    frame += 1

    player.update(dt, keyboard)

    if not enemies:
        player.on_win()
    else:
        for enemy in enemies:
            enemy.update(dt)


bad_guy_id = 1

def repr_float(f):
    s = str(f)
    left, dot, right = s.partition('.')
    if not dot:
        return s
    left = left.rjust(4, '0')
    right = right[0]
    return f"{left}.{right}"


def circle_rect_collision(
    circle_pos: Vector2D,
    circle_radius_squared: float,

    upper_left: Vector2D,
    lower_right: Vector2D):

    x, y = circle_pos

    if x < upper_left.x:
        x = upper_left.x
    elif x > lower_right.x:
        x = lower_right.x

    if y < upper_left.y:
        y = upper_left.y
    elif y > lower_right.y:
        y = lower_right.y

    delta = circle_pos - Vector2D(x, y)
    return delta.magnitude_squared <= circle_radius_squared


def detect_wall_collisions(entity):
    collisions = []
    for wall in walls:
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

class Wall:
    # remember that in Wasabi2d (0, 0) is in the upper-left.
    # x grows as we move right.
    # y grows as we move down.
    def __init__(self, upper_left, lower_right, visible=True):
        global bad_guy_id
        self.id = bad_guy_id
        bad_guy_id += 1

        self.upper_left = upper_left
        self.lower_right = lower_right
        self.width = lower_right.x - upper_left.x
        self.height = lower_right.y - upper_left.y
        self.pos = Vector2D(upper_left.x + (self.width / 2), upper_left.y + (self.height / 2))
        # print(f"WALL ul {upper_left} lr {lower_right} pos {self.pos} wxh {self.width} {self.height}")

        self.collision_edges = [
            upper_left,
            Vector2D(lower_right.x, upper_left.y),
            lower_right,
            Vector2D(upper_left.x, lower_right.y),
            ]

        if visible:
            self.layer = scene.layers[Layers.WALL_LAYER]
            self.shape = self.layer.add_rect(
                pos=self.pos,
                width=self.width,
                height=self.height,
                color=(0.25, 0.25, 0.25),
                fill = True,
            )
        else:
            self.shape = self.layer = None

    def __repr__(self):
        return f"<Wall ({repr_float(self.upper_left.x)}, {repr_float(self.upper_left.y)} x ({repr_float(self.lower_right.x)}, {repr_float(self.lower_right.y)}>"

    def _close(self):
        if self.shape:
            self.shape.delete()
            self.shape = None

    def close(self):
        walls.remove(self)
        self._close()

    def update(self, dt):
        pass

    def collide_with_entity(self, entity):
        if circle_rect_collision(
            entity.pos, player.radius_squared,
            self.upper_left,
            self.lower_right):
            return polygon_collision(self.collision_edges, entity.pos, entity.radius)
        return None


class BadGuy:
    die_on_any_collision = False

    def __init__(self):
        global bad_guy_id
        self.pos = Vector2D()
        self.id = bad_guy_id
        bad_guy_id += 1
        self.radius_squared = self.radius ** 2
        self.outer_collision_distance = (self.radius + player.outer_radius)
        self.outer_collision_distance_squared = self.outer_collision_distance ** 2
        self.body_collision_distance = (self.radius + player.body_radius)
        self.body_collision_distance_squared = self.body_collision_distance ** 2
        self.zone_collision_distance = (self.radius + player.zone_radius)
        self.zone_collision_distance_squared = self.zone_collision_distance ** 2

    def _close(self):
        self.dead = True
        self.shape.delete()

    def close(self):
        enemies.remove(self)
        self._close()

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.id} ({repr_float(self.pos.x)}, {repr_float(self.pos.y)})>"

    min_random_distance = 150
    min_random_distance_squared = min_random_distance ** 2
    random_placement_inset = 20
    def random_placement(self):
        while True:
            offset = self.random_placement_inset
            self.pos = Vector2D(
                random.randint(offset, scene.width - offset),
                random.randint(offset, scene.height - offset))

            # don't go near the player
            delta = player.pos - self.pos
            if delta.magnitude_squared < self.min_random_distance_squared:
                continue

            # don't intersect with any walls
            if detect_wall_collisions(self):
                continue

            break

    speed = 1
    radius = 1
    dead = False

    def move_to(self, v):
        # print(f"{time:8}", self, "move to", v)
        self.shape.pos = self.pos = v

        collision = player.compute_collision_with_bad_guy(self)

        if collision == CollisionType.COLLISION_WITH_ZONE:
            player.on_collision_zone(self)
            self.on_collide_zone()
        elif collision == CollisionType.COLLISION_WITH_PLAYER:
            player.on_collision_body(self)
            self.on_collide_player()
        else:
            penetration_vector = detect_wall_collisions(self)
            if penetration_vector:
                if self.die_on_any_collision:
                    self.close()
                    return
                self.pos -= penetration_vector
                self.shape.pos = self.pos


    def move_delta(self, delta):
        v = self.pos + delta
        self.move_to(v)

    def move_towards_player(self):
        delta = player.pos - self.pos
        if delta.magnitude > self.speed:
            delta = delta.scaled(self.speed)
        self.move_to(self.pos + delta)

    def push_away_from_player(self):
        delta = self.pos - player.pos
        delta2 = delta.scaled(self.body_collision_distance * 1.2)
        # print(f"push away self.pos {self.pos} player.pos {player.pos} delta {delta} delta2 {delta2}")
        self.move_to(player.pos + delta2)

    def on_collide_player(self):
        pass

    # def on_collide_shield(self):
    #     self.push_away_from_player()

    def on_collide_zone(self):
        self.on_death()

    def on_death(self):
        self.close()



class Stalker(BadGuy):
    radius = 10

    def move_towards_spot(self):
        pos = player.pos + self.spot_offset
        delta = pos - self.pos
        if delta.magnitude > self.speed:
            delta = delta.scaled(self.speed)
        self.move_to(self.pos + delta)


    def __init__(self, fast):
        super().__init__()
        if fast:
            self.speed = 1.75
            color = color=(1, 0.75, 0)
        else:
            self.speed = 0.8
            color = color=(0.8, 0.3, 0.3)

        self.shape = scene.layers[Layers.ENTITIES_LAYER].add_star(
            outer_radius=self.radius,
            inner_radius=4,
            points = 6,
            color=color,
            )
        self.random_placement()
        self.spot_high_watermark = 140
        self.spot_low_watermark = 90
        self.spot_radius_min = 30
        self.spot_radius_max = 70
        self.spot_offset = Vector2D(random.randint(self.spot_radius_min, self.spot_radius_max), 0).rotated(random.randint(0, 360))
        self.head_to_spot = True

    def update(self, dt):
        if self.dead:
            return

        # Stalkers pick a random spot near the player
        #
        # they move towards that spot until they get "close enough" to the player
        # at which point they head directly towards the player
        #
        # until they get "too far" from the player,
        # at which point they start moving towards the random spot again.
        delta = player.pos - self.pos
        distance_to_player = delta.magnitude

        threshold = self.spot_low_watermark if self.head_to_spot else self.spot_high_watermark
        self.head_to_spot = distance_to_player > threshold

        if self.head_to_spot:
            self.move_towards_spot()
        else:
            self.move_towards_player()

class Shot(BadGuy):
    radius = 2
    speed = 4
    lifetime = 2
    die_on_any_collision = True

    def __init__(self, shooter):
        super().__init__()
        self.shooter = shooter
        self.pos = Vector2D(shooter.shape.pos[0], shooter.shape.pos[1])
        self.delta = (player.pos - self.pos).scaled(self.speed)
        self.layer = scene.layers[Layers.BULLETS_LAYER]
        self.shape = self.layer.add_circle(
            radius=self.radius,
            pos=self.pos,
            color=(1, 1, 3/4),
        )
        self.expiration_date = time + self.lifetime
        sounds.enemy_shot.play()

    def update(self, dt):
        if self.dead:
            return
        if time > self.expiration_date:
            self.on_death()
            return
        self.move_delta(self.delta)

    def on_collide_shield(self):
        self.remove()



class Shooter(BadGuy):
    min_time = 0.5
    max_time = 1.5

    speed = 0.3
    radius = 8

    def __init__(self):
        super().__init__()
        self.shape = scene.layers[Layers.ENTITIES_LAYER].add_circle(
            radius=self.radius,
            color=(1/2, 0, 1),
            )
        self.random_placement()

        self._next_shot_time()

    def _next_shot_time(self):
        self.next_shot_time = time + self.min_time + (random.random() * (self.max_time - self.min_time))

    def shoot(self):
        # print("shoot!", self)
        shot = Shot(self)
        enemies.append(shot)
        self._next_shot_time()

    def update(self, dt):
        if self.dead:
            return
        self.move_towards_player()
        if time >= self.next_shot_time:
            self.shoot()



SHIFT = pygame.KMOD_LSHIFT | pygame.KMOD_RSHIFT

@event
def on_key_down(key, mod):
    if key == key.F12:
        if mod & SHIFT:
            scene.toggle_recording()
        else:
            scene.screenshot()

    if pause and (key == key.SPACE):
        close_game()
        new_game()



print("[INFO] Creating scene...")

# reminder:
#
# (0, 0) is the upper left
#
# (0, 0)---------------------------+
# |                                |
# |                                |
# |                                |
# |                                |
# |                                |
# |                                |
# |                                |
# +----------------------(1024, 768)
scene = Scene(1024, 768)
pause = False

screen_center = Vector2D(scene.width / 2, scene.height / 2)

def new_game():
    print("[INFO] Spawning player and enemies...")

    global player
    player = Player()

    global pause
    pause = False

    global bad_guy_id
    bad_guy_id = 1

    assert not (enemies or walls)

    ul = Vector2D(0, 0)
    lr = Vector2D(scene.width, scene.height)

    walls.append(Wall(ul, Vector2D(scene.width, 20)))
    walls.append(Wall(Vector2D(0, scene.height - 20), lr))

    walls.append(Wall(ul, Vector2D(20, scene.height)))
    walls.append(Wall(Vector2D(scene.width - 20, 0), lr))

    # and a wall in the middle to play with
    walls.append(Wall(Vector2D(600, 200), Vector2D(800, 400)))


    if len(sys.argv) > 1 and sys.argv[1] == "1":
        enemies.append(Stalker(fast=False))
    else:
        for i in range(15):
            enemies.append(Stalker(fast=False))

        for i in range(3):
            enemies.append(Stalker(fast=True))

        for i in range(5):
            enemies.append(Shooter())

    print("player location", player.pos)
    print("[INFO] Fight!")

def close_game():
    global player
    player.close()
    player = None

    for enemy in enemies:
        enemy._close()
    enemies.clear()

    for wall in walls:
        wall._close()
    walls.clear()

    # clear out all layers
    for layer in dir(Layers):
        if layer.startswith("_"):
            continue
        value = getattr(Layers, layer)
        scene.layers[value].clear




new_game()

run()  # keep this at the end of the file
