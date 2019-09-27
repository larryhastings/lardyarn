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
    'aim x axis': 3,
    'aim y axis': 4,
    'button up': 3,
    'button down': 0,
    'button left': 2,
    'button right': 1,
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


TAU = 2 * math.pi


def angle_diff(a, b):
    """Subtract angle b from angle a.

    Return the difference in the smallest direction.
    """
    diff = (a - b) % TAU
    return min(diff, diff - TAU, key=abs)


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

        self.movement = Vector2D()

        # new "zone of destruction"
        self.normal_zone_color = (0.3, 0.3, 0.8)
        self.flashing_zone_color = (0.9, 0.9, 1)
        if 1:
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
            if polygon_collision(self.zone_triangle, bad_guy):
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

        self.movement = self.movement * air_resistance ** dt + acceleration_scale * acceleration * dt
        if self.movement.magnitude > max_speed:
            self.movement = self.movement.scaled(max_speed)

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
        movement_this_frame = self.movement * dt
        self.pos += movement_this_frame
        if self.pos == starting_pos:
            return

        hit_walls = []
        for wall in walls:
            if wall.collide_with_entity(self) == CollisionType.COLLISION_WITH_WALL:
                hit_walls.append(wall)

        if hit_walls:
            # we hit one or more walls!
            # replay a % of the movement so we move as much as possible without hitting.
            factor = 1.0
            cumulative_factor = 0
            working_pos = starting_pos
            for i in range(10):
                factor /= 2
                try_factor = cumulative_factor + factor
                partial_movement = movement_this_frame * try_factor

                self.pos = starting_pos + partial_movement
                hit = False
                for wall in hit_walls:
                    hit = wall.collide_with_entity(self) == CollisionType.COLLISION_WITH_WALL
                    if hit:
                        break
                if hit:
                    self.pos = working_pos
                else:
                    cumulative_factor = try_factor
                    working_pos = self.pos

            final_pos = self.pos

            # and zero out the movement vector of all directions in which we hit the wall
            # if self.pos.x != old_pos.x:
            #     self.movement.x = 0
            # if self.pos.y != old_pos.y:
            #     self.movement.y = 0

            if 0:
                # test zeroing out each component of movement_this_frame
                # if the resulting movement vector doesn't result in hitting the wall,
                # leave it in, otherwise zero it out.
                test_vector = movement_this_frame
                test_vector.x = 0
                self.pos = starting_pos + test_vector
                hit = False
                for wall in hit_walls:
                    if wall.collide_with_entity(self) == CollisionType.COLLISION_WITH_WALL:
                        hit = True
                        break
                if hit:
                    self.movement.x = 0

                test_vector = movement_this_frame
                test_vector.y = 0
                self.pos = starting_pos + test_vector
                hit = False
                for wall in hit_walls:
                    if wall.collide_with_entity(self) == CollisionType.COLLISION_WITH_WALL:
                        hit = True
                        break
                if hit:
                    self.movement.y = 0
                # print(f"hit walls {hit_walls} movement {self.movement}")

            self.movement = Vector2D()

        self.zone.pos = self.shape.pos = self.pos

        current_speed = self.movement.magnitude
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

        global max_speed_measured
        new_max = max(max_speed_measured, current_speed)
        if new_max > max_speed_measured:
            max_speed_measured = new_max
            print("new max speed measured:", max_speed_measured)

        def update_shield(source, vector):
            dist, degrees = vector.as_polar()
            angle = math.radians(degrees)

            delta = abs(self.zone_angle - angle)
            # krazy kode to avoid the "sword goes crazy when you flip from 179° to 181°" problem
            # aka the "+math.pi to -math.pi" problem
            if delta > math.pi:
                if angle < self.zone_angle:
                    angle += math.tau
                else:
                    angle -= math.tau
                delta = abs(self.zone_angle - angle)
                assert delta <= math.pi

            if delta <= max_shield_delta:
                self.zone_angle = angle
            elif angle < self.zone_angle:
                self.zone_angle -= max_shield_delta
            else:
                self.zone_angle += max_shield_delta

            self.zone_angle = normalize_angle(self.zone_angle)
            assert -math.pi <= self.zone.angle <= math.pi

            # update the shape
            # self.shield.angle = self.zone_angle
            self.zone.angle = self.zone_angle

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





movement_keys = {
    keys.UP:    Vector2D(+0, -1),
    keys.DOWN:  Vector2D(+0, +1),
    keys.LEFT:  Vector2D(-1, +0),
    keys.RIGHT: Vector2D(+1, +0),
}
movement_keys[keys.W] = movement_keys[keys.UP]
movement_keys[keys.S] = movement_keys[keys.DOWN]
movement_keys[keys.A] = movement_keys[keys.LEFT]
movement_keys[keys.D] = movement_keys[keys.RIGHT]


shield_keys = {
    keys.I: Vector2D(+0, -1),
    keys.K: Vector2D(+0, +1),
    keys.J: Vector2D(-1, +0),
    keys.L: Vector2D(+1, +0),
}


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
    use_right_stick = (
        (max(settings['aim x axis'], settings['aim y axis']) < axes)
        and
        (min(settings['aim x axis'], settings['aim y axis']) >= 0))

    buttons = stick.get_numbuttons()
    noun = "button" if buttons == 1 else "buttons"
    print(f"[INFO] {buttons} joystick {noun}")
    use_face_buttons = (
        (max(settings['button up'], settings['button down'], settings['button left'], settings['button right']) < buttons)
        and
        (min(settings['button up'], settings['button down'], settings['button left'], settings['button right']) >= 0))

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

print("[INFO] use left stick?", use_left_stick)
print("[INFO] use right stick?", use_right_stick)
print("[INFO] use hat?", use_hat)
print("[INFO] use face buttons for shield?", use_face_buttons)


shield_buttons = {
    settings['button up'   ]: Vector2D(+0, -1),
    settings['button down' ]: Vector2D(+0, +1),
    settings['button left' ]: Vector2D(-1, +0),
    settings['button right']: Vector2D(+1, +0),
}


# dan's original values
acceleration_scale = 1000
air_resistance = 0.01
max_speed = 1000.0

# tweaked faster values
acceleration_scale = 1800
air_resistance = 0.07
max_speed = 700 # max observed speed is 691 anyway

max_shield_delta = math.tau / 6

time = 0

enemies = []
walls = []

@event
def update(dt, keyboard):
    global time

    if keyboard.escape:
        sys.exit("[INFO] Quittin' time!")

    if pause:
        for button in (0, 1, 2, 3):
            if stick.get_button(button):
                close_game()
                new_game()
        return

    time += dt

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
            return CollisionType.COLLISION_WITH_WALL
        return CollisionType.NO_COLLISION


class BadGuy:

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
            for wall in walls:
                if wall.collide_with_entity(self) != CollisionType.NO_COLLISION:
                    break
            else:
                break
            continue

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

        if 0:
            vector_to_player = player.pos - self.pos
            distance_squared = vector_to_player.magnitude_squared
            intersect_outer_radius = distance_squared <= self.outer_collision_distance_squared
            if intersect_outer_radius:
                # print(f"{self} interecting outer radius")
                # are we intersecting with the zone?
                if not player.zone_layer.visible:
                    # print("    zone inactive (player is too slow)")
                    pass
                else:
                    # print(f"    player center {player.pos} zone angle {player.zone_angle} zone center {player.zone_center}")
                    vector_to_zone = player.zone_center - self.pos
                    intersect_zone_radius = vector_to_zone.magnitude_squared < self.zone_collision_distance_squared
                    # print(f"    interecting zone? {intersect_zone_radius}")
                    if intersect_zone_radius:
                        collision = player.on_collision_zone(self)
                        if collision == CollisionType.COLLISION_WITH_ZONE:
                            self.on_collide_zone()

                if self.dead:
                    # print(f"    dead!")
                    return

                intersect_body_radius = distance_squared <= self.body_collision_distance_squared
                # print(f"    interecting body? {intersect_body_radius}")

                if intersect_body_radius:
                    collision = player.on_collision_body(self)
                    assert collision != CollisionType.COLLISION_WITH_ZONE
                    if collision == CollisionType.NO_COLLISION:
                        return

                    assert collision == CollisionType.COLLISION_WITH_PLAYER
                    self.on_collide_player()

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
        self.dead = True
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
        enemies.append(Stalker(fast=True))
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


new_game()

run()  # keep this at the end of the file
