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

devicename=settings.get('mixer devicename')
pygame.mixer.pre_init(devicename=devicename)
pygame.init()
pygame.mixer.init()

import wasabi2d
from wasabi2d import Scene, run, event, clock, Vector2, keys, sounds
import pygame.mouse
from pygame import joystick


class CollisionType(enum.IntEnum):
    INVALID = 0
    COLLISION_WITH_PLAYER = 1
    COLLISION_WITH_SHIELD = 2
    COLLISION_WITH_SWORD = 3

scene = Scene(1024, 768)
pause = False

# The rest of your code goes here.

screen_center = Vector2(scene.width / 2, scene.height / 2)

def normalize_angle(theta):
    if theta > math.pi:
        theta -= math.tau
    elif theta < -math.pi:
        theta += math.tau
    return theta

class Player:
    radius = 10
    sword_radius = 20
    shield_arc = math.tau / 4 # how far the shield extends
    shield_angle = 0
    dead = False

    def __init__(self):
        self.pos = Vector2(screen_center)
        self.shape = scene.layers[0].add_circle(
            radius=self.radius,
            pos=self.pos,
            color=(0, 1/2, 0),
            )

        # self.shield = scene.layers[1].add_sprite(
        #     'swordandshield',
        #     pos=(scene.width / 2, scene.height / 2),
        #     )
        inner = []
        outer = []
        # radius_delta = 2
        inner_radius = self.radius - 3
        outer_radius = self.radius + 1
        # lame, range only handles ints. duh!
        start = math.degrees(-self.shield_arc / 2)
        stop = math.degrees(self.shield_arc / 2)
        step = (stop - start) / 12
        theta = start
        def append(theta):
            # even lamer: from_polar()
            # MUST BE CALLED ON AN INSTANCE
            # TAKES AN ARGUMENT, WHICH MUST BE A Vector2
            # IGNORES ITS OWN x AND y, OVERWRITING THEM
            # WTF
            v = Vector2(inner_radius, theta)
            v.from_polar(v)
            inner.append(tuple(v))

            v = Vector2(outer_radius, theta)
            v.from_polar(v)
            outer.append(tuple(v))

        while theta < stop:
            append(theta)
            theta += step
        append(stop)

        # now make the sword pointy!
        middle = len(outer) // 2
        v = Vector2(outer[middle])
        radius, theta = v.as_polar()
        v.from_polar((self.sword_radius, theta))
        outer[middle] = tuple(v)

        inner.reverse()
        outer.extend(inner)
        vertices = outer
        self.shield = scene.layers[1].add_polygon(vertices, fill=True, color=(1, 1, 1))
        self.movement = Vector2()

    def update(self, dt, keyboard):
        acceleration = Vector2()
        for key, vector in movement_keys.items():
            if keyboard[key]:
                acceleration += vector

        if use_hat:
            x, y = stick.get_hat(0)
            if x or y:
                acceleration += Vector2(x, -y)

        if use_left_stick:
            stick_vector = Vector2(
                stick.get_axis(0),
                stick.get_axis(1)
            )
            stick_magnitude = stick_vector.magnitude()
            if stick_magnitude >= 1e-2:
                acceleration += stick_vector.normalize() * min(1.0, stick_magnitude)

        self.movement = self.movement * air_resistance ** dt + acceleration_scale * acceleration * dt
        if self.movement.magnitude() > max_speed:
            self.movement.scale_to_length(max_speed)

        self.pos += self.movement * dt
        self.shield.pos = self.shape.pos = self.pos

        def update_shield(source, vector):
            dist, degrees = vector.as_polar()
            angle = math.radians(degrees)

            delta = abs(self.shield_angle - angle)
            # krazy kode to avoid the "sword goes crazy when you flip from 179° to 181°" problem
            # aka the "+math.pi to -math.pi" problem
            if delta > math.pi:
                if angle < self.shield_angle:
                    angle += math.tau
                else:
                    angle -= math.tau
                delta = abs(self.shield_angle - angle)
                assert delta <= math.pi

            if delta <= max_shield_delta:
                self.shield_angle = angle
            elif angle < self.shield_angle:
                self.shield_angle -= max_shield_delta
            else:
                self.shield_angle += max_shield_delta

            self.shield_angle = normalize_angle(self.shield_angle)

            # update the shape
            self.shield.angle = self.shield_angle
            assert -math.pi <= self.shield.angle <= math.pi

        mouse_movement = pygame.mouse.get_rel()
        if mouse_movement[0] or mouse_movement[1]:
            update_shield("mouse", Vector2(mouse_movement))

        direction = Vector2()
        for key, vector in shield_keys.items():
            if keyboard[key]:
                direction += vector
        if direction:
            update_shield("keyboard", direction)

        if use_right_stick:
            stick_rx = stick.get_axis(3)
            stick_ry = stick.get_axis(4)
            # print(stick.get_axis(2), stick.get_axis(3), stick.get_axis(4), stick.get_axis(5))
            if stick_rx or stick_ry:
                update_shield("right stick", Vector2(stick_rx, stick_ry))

        # pressed = set()
        # for i in range(buttons):
        #     if stick.get_button(i):
        #         pressed.add(i)
        # if pressed:
        #     print(pressed)
        if use_face_buttons:
            direction = Vector2()
            for button, vector in shield_buttons.items():
                if stick.get_button(button):
                    direction += vector
            if direction:
                update_shield("buttons", direction)

    def on_collision(self, other):
        """
        Returns bool indicating whether or not the collision was on the player or on the shield.
        True for it hit the player, false for it hit the shield.
        """
        global pause
        if self.dead:
            return CollisionType.INVALID
        # calculate whether or not it hit the shield first
        # simply: is the angle to other within the two angles
        # of the shield's edges?
        #
        # note: we guarantee when we calculate it that
        # -math.pi <= self.shield_angle <= math.pi
        delta = other.pos - self.pos
        magnitude, theta = delta.as_polar()
        theta = math.radians(theta)

        start = normalize_angle(self.shield_angle - self.shield_arc)
        end   = normalize_angle(self.shield_angle + self.shield_arc)

        if end < start:
            # the shield crosses 180 degrees! handle special
            within_shield = ((start <= theta <= math.pi) and (-math.pi <= theta <= end))
        else:
            within_shield = start <= theta <= end

        if within_shield:
            print("player ignore collision with", other)
            return CollisionType.COLLISION_WITH_SHIELD

        print("PLAYER HIT", other)
        self.dead = True
        pause = True
        sounds.hit.play()
        self.shape.delete()
        self.shield.delete()

        self.game_over_text = scene.layers[2].add_label(
            text = "YOU DIED\nGAME OVER\nPRESS ESCAPE TO QUIT",
            fontsize = 44.0,
            align = "center",
            pos = screen_center,
            )

        return CollisionType.COLLISION_WITH_PLAYER





player = Player()


movement_keys = {
    keys.W: Vector2(+0, -1),
    keys.S: Vector2(+0, +1),
    keys.A: Vector2(-1, +0),
    keys.D: Vector2(+1, +0),
}


shield_keys = {
    keys.I: Vector2(+0, -1),
    keys.K: Vector2(+0, +1),
    keys.J: Vector2(-1, +0),
    keys.L: Vector2(+1, +0),
}


joystick.init()
stick = joystick.Joystick(0)
stick.init()
axes = stick.get_numaxes()
print("joystick AXES", axes)
use_left_stick = axes >= 2
use_right_stick = axes >= 5

buttons = stick.get_numbuttons()
print("joystick BUTTONS", buttons)
use_face_buttons = buttons >= 4

hats = stick.get_numhats()
print("joystick HATS", hats)
use_hat = hats >= 1

print("use left stick?", use_left_stick)
print("use right stick?", use_right_stick)
print("use hat?", use_hat)
print("use face buttons for shield?", use_face_buttons)


shield_buttons = {
    settings['button up'   ]: Vector2(+0, -1),
    settings['button down' ]: Vector2(+0, +1),
    settings['button left' ]: Vector2(-1, +0),
    settings['button right']: Vector2(+1, +0),
}


# dan's original values
acceleration_scale = 1000
air_resistance = 0.01
max_speed = 1000.0

# tweaked faster values
acceleration_scale = 2000
air_resistance = 0.05
max_speed = 100000.0

max_shield_delta = math.tau / 6

time = 0

enemies = []

@event
def update(dt, keyboard):
    global time

    if keyboard.escape:
        sys.exit("quittin' time!")

    if pause:
        return

    time += dt

    player.update(dt, keyboard)

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

class BadGuy:
    def __init__(self):
        global bad_guy_id
        self.pos = Vector2()
        self.id = bad_guy_id
        bad_guy_id += 1

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.id} ({repr_float(self.pos.x)}, {repr_float(self.pos.y)})>"

    min_random_distance = 150
    min_random_distance_squared = min_random_distance ** 2
    def random_placement(self):
        while True:
            pos = Vector2(random.randint(0, scene.width), random.randint(0, scene.height))
            delta = player.pos - pos
            distance_squared = delta.magnitude_squared()
            if distance_squared > self.min_random_distance_squared:
                self.pos = pos
                break

    speed = 1
    radius = 1

    def move_to(self, v):
        self.shape.pos = self.pos = v
        vector_to_player = player.pos - self.pos
        distance_squared = vector_to_player.magnitude_squared()
        collision_distance = (self.radius + player.radius)
        collision_distance_squared = collision_distance * collision_distance
        if distance_squared <= collision_distance_squared:
            touched = player.on_collision(self)
            if touched == CollisionType.COLLISION_WITH_PLAYER:
                self.on_collide_player()
            elif touched == CollisionType.COLLISION_WITH_SHIELD:
                self.on_collide_shield()
            elif touched == CollisionType.COLLISION_WITH_SWORD:
                self.on_collide_sword()
            self.remove()
            return

    def on_collide_player(self):
        pass

    def on_collide_shield(self):
        pass

    def on_collide_sword(self):
        self.remove()

    def move_delta(self, delta):
        v = self.pos + delta
        self.move_to(v)

    def move_towards_player(self):
        delta = player.pos - self.pos
        if delta.magnitude() > self.speed:
            delta.scale_to_length(self.speed)
        self.move_delta(delta)

    def remove(self):
        enemies.remove(self)
        self.shape.delete()


class Stalker(BadGuy):
    radius = 10
    speed = 2

    def __init__(self):
        super().__init__()
        self.shape = scene.layers[0].add_star(
            outer_radius=self.radius,
            inner_radius=4,
            points = 6,
            color=(1, 1/2, 0),
            )
        self.random_placement()

    def on_collide_shield(self):
        pass

    def update(self, dt):
        self.move_towards_player()

class Shot(BadGuy):
    radius = 2
    speed = 5
    lifetime = 2

    def __init__(self, shooter):
        super().__init__()
        self.shooter = shooter
        self.pos = Vector2(shooter.shape.pos[0], shooter.shape.pos[1])
        self.delta = player.pos - self.pos
        self.delta.scale_to_length(self.speed)
        self.layer = scene.layers[-1]
        self.shape = self.layer.add_circle(
            radius=self.radius,
            pos=self.pos,
            color=(1, 1, 3/4),
        )
        self.expiration_date = time + self.lifetime
        sounds.enemy_shot.play()

    def update(self, dt):
        if time > self.expiration_date:
            self.remove()
            return
        self.move_delta(self.delta)


class Shooter(BadGuy):
    min_time = 0.5
    max_time = 1.5

    speed = 0.5
    radius = 8

    def __init__(self):
        super().__init__()
        self.shape = scene.layers[0].add_circle(
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
        self.move_towards_player()
        if time >= self.next_shot_time:
            self.shoot()



for i in range(15):
    enemies.append(Stalker())

for i in range(8):
    enemies.append(Shooter())


run()  # keep this at the end of the file
