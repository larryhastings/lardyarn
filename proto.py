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

devicename=settings.get('mixer devicename')
pygame.mixer.pre_init(devicename=devicename)
pygame.init()
try:
    pygame.mixer.init()
except pygame.error as e:
    print("Warning: sound not working")
    print("    ", e)
    # call pre-init again with no devicename
    # this will reset back to the default
    # which ALSO won't work, but pygame works better this way
    pygame.mixer.pre_init(devicename=None)
    pygame.mixer.init()

import wasabi2d
from wasabi2d import Scene, run, event, clock, Vector2, keys, sounds
import pygame.mouse
from pygame import joystick


class CollisionType(enum.IntEnum):
    NO_COLLISION = 0
    COLLISION_WITH_PLAYER = 1
    COLLISION_WITH_ZONE = 2

class Layers(enum.IntEnum):
    ENTITIES_LAYER = 0
    BULLETS_LAYER = 1
    ZONE_LAYER = 2
    TEXT_LAYER = 3


TAU = 2 * math.pi


def angle_diff(a, b):
    """Subtract angle b from angle a.

    Return the difference in the smallest direction.
    """
    diff = (a - b) % TAU
    return min(diff, diff - TAU, key=abs)


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

    # max speed measured: 590 and change
    zone_activation_speed = 350
    zone_grace_period = 0.1
    zone_grace_timeout = 0

    zone_center_distance = body_radius + (zone_radius / 2)
    zone_flash_until = 0

    def __init__(self):
        self.pos = Vector2(screen_center)
        self.shape = scene.layers[Layers.ENTITIES_LAYER].add_circle(
            radius=self.body_radius,
            pos=self.pos,
            color=(0, 1/2, 0),
            )

        self.movement = Vector2()


        # new "zone of destruction"
        self.normal_zone_color = (0.3, 0.3, 0.8)
        self.flashing_zone_color = (0.9, 0.9, 1)
        if 0:
            # draw zone as arc
            vertices = []
            points_on_zone = 12
            # lame, range only handles ints. duh!
            start = math.degrees(-self.zone_arc / 2)
            stop = math.degrees(self.zone_arc / 2)
            step = (stop - start) / points_on_zone
            theta = start

            def append(theta):
                # even lamer: from_polar()
                # MUST BE CALLED ON AN INSTANCE
                # TAKES AN ARGUMENT, WHICH MUST BE A Vector2
                # IGNORES ITS OWN x AND y, OVERWRITING THEM
                # WTF
                v = Vector2(self.zone_radius, theta)
                v.from_polar(v)
                v.x += self.body_radius
                vertices.append(tuple(v))
            while theta < stop:
                append(theta)
                theta += step
        else:
            # draw zone as circl3e, for quick prototyping
            # draw zone as arc
            vertices = []
            for theta in range(0, 360, 10):
                v = Vector2(self.zone_radius / 2, theta)
                v.from_polar(v)
                v.x += self.zone_center_distance
                vertices.append(tuple(v))

        self.zone_layer = scene.layers[Layers.ZONE_LAYER]
        self.zone = self.zone_layer.add_polygon(vertices, fill=True, color=self.normal_zone_color)
        self.zone_center = self.pos + Vector2(self.zone_center_distance, 0)
        self.zone_layer_active = False
        self.zone_layer.visible = False

        if 0:
            # old sword & shield

            # self.shield = scene.layers[Layers.ZONE_LAYER].add_sprite(
            #     'swordandshield',
            #     pos=(scene.width / 2, scene.height / 2),
            #     )
            inner = []
            outer = []
            # radius_delta = 2
            inner_radius = self.body_radius - 3
            outer_radius = self.body_radius + 1
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
            self.shield = scene.layers[Layers.ZONE_LAYER].add_polygon(vertices, fill=True, color=(1, 1, 1))

    def update(self, dt, keyboard):
        if self.zone_flash_until and (self.zone_flash_until < time):
            self.zone_flash_until = 0
            self.zone.color = self.normal_zone_color

        acceleration = Vector2()
        for key, vector in movement_keys.items():
            if keyboard[key]:
                acceleration += vector

        if use_hat:
            x, y = stick.get_hat(0)
            if x or y:
                acceleration += Vector2(x, -y)

        if use_left_stick:
            acceleration += Vector2(
                stick.get_axis(0),
                stick.get_axis(1)
            )

        if acceleration.magnitude() > 1.0:
            acceleration.normalize_ip()

        self.movement = self.movement * air_resistance ** dt + acceleration_scale * acceleration * dt
        if self.movement.magnitude() > max_speed:
            self.movement.scale_to_length(max_speed)

        # Rotate to face the direction of acceleration
        TURN = 12  # radians / s at full acceleration

        da, accel_angle = acceleration.as_polar()
        accel_angle = math.radians(accel_angle)
        delta = angle_diff(accel_angle, self.zone_angle)
        if delta < 0:
            self.zone_angle += max(dt * da * -TURN, delta)
        else:
            self.zone_angle += min(dt * da * TURN, delta)
        self.zone.angle = self.zone_angle = normalize_angle(self.zone_angle)

        self.pos += self.movement * dt
        self.zone.pos = self.shape.pos = self.pos

        current_speed = self.movement.magnitude()
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

#        mouse_movement = pygame.mouse.get_rel()
#        if mouse_movement[0] or mouse_movement[1]:
#            update_shield("mouse", Vector2(mouse_movement))

#        direction = Vector2()
#        for key, vector in shield_keys.items():
#            if keyboard[key]:
#                direction += vector
#        if direction:
#            update_shield("keyboard", direction)

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
#        if use_face_buttons:
#            direction = Vector2()
#            for button, vector in shield_buttons.items():
#                if stick.get_button(button):
#                    direction += vector
#            if direction:
#                update_shield("buttons", direction)

        self.zone_center = self.pos + Vector2(math.cos(self.zone_angle) * self.zone_center_distance, math.sin(self.zone_angle) * self.zone_center_distance)

    def on_collision_zone(self, other):
        """
        self and body are within sword radius.  are they colliding?
        Returns enum indicating type of collision.
        """
        self.zone_flash_until = time + 0.1
        self.zone.color = self.flashing_zone_color
        sounds.zap.play()
        return CollisionType.COLLISION_WITH_ZONE


    def on_collision_body(self, other):
        """
        self and body are within body radius. they're colliding, but how?
        Returns enum indicating type of collision.
        """
        if self.dead:
            return CollisionType.NO_COLLISION

        self.on_death(other)
        return CollisionType.COLLISION_WITH_PLAYER


    def on_death(self, other):
        global pause
        print("PLAYER HIT", other, "BANG!")
        self.dead = True
        pause = True
        sounds.hit.play()
        # self.shape.delete()
        # self.shield.delete()

        self.game_over_text = scene.layers[Layers.TEXT_LAYER].add_label(
            text = "YOU DIED\nGAME OVER\nPRESS ESCAPE TO QUIT",
            fontsize = 44.0,
            align = "center",
            pos = screen_center,
            )

    def on_win(self):
        global pause
        print("PLAYER WINS!")
        self.dead = True
        pause = True
        # sounds.hit.play()
        # self.shape.delete()
        # self.shield.delete()

        self.game_won_text = scene.layers[Layers.TEXT_LAYER].add_label(
            text = "A WINNER IS YOU!\ngame over\npress Escape to quit",
            fontsize = 44.0,
            align = "center",
            pos = screen_center,
            )
        sounds.game_won.play()





player = Player()


movement_keys = {
    keys.UP:    Vector2(+0, -1),
    keys.DOWN:  Vector2(+0, +1),
    keys.LEFT:  Vector2(-1, +0),
    keys.RIGHT: Vector2(+1, +0),
}
movement_keys[keys.W] = movement_keys[keys.UP]
movement_keys[keys.S] = movement_keys[keys.DOWN]
movement_keys[keys.A] = movement_keys[keys.LEFT]
movement_keys[keys.D] = movement_keys[keys.RIGHT]


shield_keys = {
    keys.I: Vector2(+0, -1),
    keys.K: Vector2(+0, +1),
    keys.J: Vector2(-1, +0),
    keys.L: Vector2(+1, +0),
}


joystick.init()
which_joystick = settings['joystick']
if which_joystick < joystick.get_count():
    stick = joystick.Joystick(which_joystick)
    stick.init()
    axes = stick.get_numaxes()
    print("joystick AXES", axes)
    use_left_stick = (
        (max(settings['move x axis'], settings['move y axis']) < axes)
        and
        (min(settings['move x axis'], settings['move y axis']) >= 0))
    use_right_stick = (
        (max(settings['aim x axis'], settings['aim y axis']) < axes)
        and
        (min(settings['aim x axis'], settings['aim y axis']) >= 0))

    buttons = stick.get_numbuttons()
    print("joystick BUTTONS", buttons)
    use_face_buttons = (
        (max(settings['button up'], settings['button down'], settings['button left'], settings['button right']) < buttons)
        and
        (min(settings['button up'], settings['button down'], settings['button left'], settings['button right']) >= 0))

    hats = stick.get_numhats()
    print("joystick HATS", hats)
    use_hat = hats >= 1
    use_hat = (
        (settings['hat'] < hats)
        and
        (settings['hat'] >= 0))
else:
    print(f"insufficient joysticks!  we want joystick #{which_joystick} but only {joystick.get_count()} joysticks detected.")
    use_left_stick = use_right_stick = use_face_buttons = use_hat = False

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
acceleration_scale = 1800
air_resistance = 0.07
max_speed = 700 # max observed speed is 691 anyway

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

class BadGuy:

    def __init__(self):
        global bad_guy_id
        self.pos = Vector2()
        self.id = bad_guy_id
        bad_guy_id += 1
        self.radius_squared = self.radius ** 2
        self.outer_collision_distance = (self.radius + player.outer_radius)
        self.outer_collision_distance_squared = self.outer_collision_distance ** 2
        self.body_collision_distance = (self.radius + player.body_radius)
        self.body_collision_distance_squared = self.body_collision_distance ** 2
        self.zone_collision_distance = (self.radius + player.zone_radius)
        self.zone_collision_distance_squared = self.zone_collision_distance ** 2

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
    dead = False

    def move_to(self, v):
        # print(f"{time:8}", self, "move to", v)
        self.shape.pos = self.pos = v
        vector_to_player = player.pos - self.pos
        distance_squared = vector_to_player.magnitude_squared()
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
                intersect_zone_radius = vector_to_zone.magnitude_squared() < self.zone_collision_distance_squared
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
        if delta.magnitude() > self.speed:
            delta.scale_to_length(self.speed)
        self.move_to(self.pos + delta)

    def push_away_from_player(self):
        delta = self.pos - player.pos
        delta2 = Vector2(delta)
        delta2.scale_to_length(self.body_collision_distance * 1.2)
        # print(f"push away self.pos {self.pos} player.pos {player.pos} delta {delta} delta2 {delta2}")
        self.move_to(player.pos + delta2)

    def remove(self):
        enemies.remove(self)
        self.shape.delete()

    def on_collide_player(self):
        pass

    # def on_collide_shield(self):
    #     self.push_away_from_player()

    def on_collide_zone(self):
        self.on_death()

    def on_death(self):
        self.dead = True
        self.remove()



class Stalker(BadGuy):
    radius = 10

    def move_towards_spot(self):
        pos = player.pos + self.spot_offset
        delta = pos - self.pos
        if delta.magnitude() > self.speed:
            delta.scale_to_length(self.speed)
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
        self.spot_offset = Vector2(random.randint(self.spot_radius_min, self.spot_radius_max), 0)
        self.spot_offset.rotate_ip(random.randint(0, 360))
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
        distance_to_player = delta.magnitude()
        if self.head_to_spot:
            self.head_to_spot = distance_to_player > self.spot_low_watermark
        else:
            self.head_to_spot = distance_to_player < self.spot_high_watermark
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
        self.pos = Vector2(shooter.shape.pos[0], shooter.shape.pos[1])
        self.delta = player.pos - self.pos
        self.delta.scale_to_length(self.speed)
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


if len(sys.argv) > 1 and sys.argv[1] == "1":
    enemies.append(Stalker(fast=False))
else:
    for i in range(15):
        enemies.append(Stalker(fast=False))

    for i in range(3):
        enemies.append(Stalker(fast=True))

    for i in range(5):
        enemies.append(Shooter())


SHIFT = pygame.KMOD_LSHIFT | pygame.KMOD_RSHIFT

@event
def on_key_down(key, mod):
    if key == key.F12:
        if mod & SHIFT:
            scene.toggle_recording()
        else:
            scene.screenshot()


run()  # keep this at the end of the file
