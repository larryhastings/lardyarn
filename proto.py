import sys
import math
import random
import wasabi2d
from wasabi2d import Scene, run, event, clock, Vector2, keys
import pygame.mouse
from pygame import joystick


scene = Scene(1024, 768)

# The rest of your code goes here.

screen_center = Vector2(scene.width / 2, scene.height / 2)

class Player:
    def __init__(self):
        self.pos = screen_center
        self.shape = scene.layers[0].add_circle(
            radius=10,
            pos=self.pos,
            color=(0, 128, 0),
        )

player = Player()

def player_collided(other):
    print("Player collided with", other)

sword_and_shield = scene.layers[1].add_sprite(
    'swordandshield',
    pos=(scene.width / 2, scene.height / 2),
)
sword_and_shield.scale=1.3

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
    3: Vector2(+0, -1),
    0: Vector2(+0, +1),
    2: Vector2(-1, +0),
    1: Vector2(+1, +0),
}


movement = Vector2()
# dan's original values
acceleration_scale = 1000
air_resistance = 0.01
max_speed = 1000.0

# tweaked faster values
acceleration_scale = 2000
air_resistance = 0.05
max_speed = 100000.0

shield_angle = 0
max_shield_delta = math.tau / 6

time = 0

enemies = []

@event
def update(dt, keyboard):
    global time
    global movement
    global shield_angle

    time += dt

    if keyboard.escape:
        sys.exit("quittin' time!")

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

    movement = movement * air_resistance ** dt + acceleration_scale * acceleration * dt
    if movement.magnitude() > max_speed:
        movement.scale_to_length(max_speed)

    player.pos += movement * dt
    sword_and_shield.pos = player.shape.pos = player.pos

    def update_shield(source, vector):
        dist, degrees = vector.as_polar()
        angle = math.radians(degrees)

        delta = abs(sword_and_shield.angle - angle)
        # krazy kode to avoid the "sword goes crazy when you flip from 179° to 181°" problem
        # aka the "+math.pi to -math.pi" problem
        if delta > math.pi:
            if angle < sword_and_shield.angle:
                angle += math.tau
            else:
                angle -= math.tau
            delta = abs(sword_and_shield.angle - angle)
            assert delta <= math.pi

        if delta <= max_shield_delta:
            sword_and_shield.angle = angle
        elif angle < sword_and_shield.angle:
            sword_and_shield.angle -= max_shield_delta
        else:
            sword_and_shield.angle += max_shield_delta

        if sword_and_shield.angle > math.tau:
            sword_and_shield.angle -= math.tau
        elif sword_and_shield.angle < -math.tau:
            sword_and_shield.angle += math.tau

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

    for enemy in enemies:
        enemy.update(dt)


random_vector_offset = Vector2(screen_center.y / 2, 0)

class BadGuy:
    def __init__(self):
        self.pos = Vector2()

    min_random_distance = 150
    min_random_distance_squared = min_random_distance ** 2
    def random_placement(self):
        # displacement = random_vector_offset.rotate(random.random() * 360)
        # self.shape.pos = self.pos = screen_center + displacement
        while True:
            pos = Vector2(random.randint(0, scene.width), random.randint(0, scene.height))
            delta = player.pos - pos
            distance_squared = delta.magnitude_squared()
            if distance_squared > self.min_random_distance_squared:
                self.pos = pos
                print("enemy random pos", self.pos)
                break

    speed = 1

    def move_towards_player(self):
        delta = player.pos - self.pos
        if delta.magnitude() <= self.speed:
            self.shape.pos = player.pos
            player_collided(self)
            self.remove()
            return
        delta.scale_to_length(self.speed)
        self.pos += delta
        self.shape.pos = self.pos

    def remove(self):
        enemies.remove(self)
        self.shape.delete()


class Stalker(BadGuy):
    speed = 2

    def __init__(self):
        super().__init__()
        self.shape = scene.layers[0].add_star(
            outer_radius=10,
            inner_radius=4,
            points = 6,
            color=(255, 128, 0),
            )
        self.random_placement()

    def update(self, dt):
        self.move_towards_player()

class Shot(BadGuy):
    speed = 5
    lifetime = 2

    def __init__(self, shooter):
        super().__init__()
        self.shooter = shooter
        self.pos = Vector2(shooter.shape.pos[0], shooter.shape.pos[1])
        self.layer = scene.layers[-1]
        self.shape = self.layer.add_circle(
            radius=2,
            pos=self.pos,
            color="white",
        )
        self.after = time + self.lifetime

    def update(self, dt):
        if time > self.lifetime:
            self.remove()
            return
        self.move_towards_player()


class Shooter(BadGuy):
    min_time = 0.5
    max_time = 1.5

    speed = 0.5

    def __init__(self):
        super().__init__()
        self.shape = scene.layers[0].add_rect(
            width=10,
            height=10,
            fill=True,
            color=(128, 0, 255),
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
