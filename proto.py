import sys

stdout = sys.stdout
sys.stdout = None
import pygame
sys.stdout = stdout

import math
import pygame.mouse
from pygame import joystick
from pygame.locals import *
import wasabi2d
from wasabi2d import Scene, run, event, clock, Vector2


scene = Scene(1024, 768)

# The rest of your code goes here.

circle = scene.layers[0].add_circle(
    radius=10,
    pos=(scene.width / 2, scene.height / 2),
    color=(0, 128, 0),
)

sword_and_shield = scene.layers[1].add_sprite(
    'swordandshield',
    pos=(scene.width / 2, scene.height / 2),
)
sword_and_shield.scale=1.3

movement_keys = {
    K_w: Vector2(+0, -1),
    K_s: Vector2(+0, +1),
    K_a: Vector2(-1, +0),
    K_d: Vector2(+1, +0),
}

print(movement_keys)

joystick.init()
stick = joystick.Joystick(0)
stick.init()

movement = Vector2()
acceleration = 7
air_resistance = 0.6
max_speed = 30.0

shield_angle = 0
max_shield_delta = math.tau / 6


from pygame.key import get_pressed

def move_winky():
    global movement
    global shield_angle
    keys = get_pressed()
    if keys[K_ESCAPE]:
        sys.exit("quittin' time!")
    direction = Vector2()
    for key, vector in movement_keys.items():
        if keys[key]:
            direction += vector
    stick_x = stick.get_axis(0)
    stick_y = stick.get_axis(1)
    if stick_x or stick_y:
        stick_vector = Vector2(stick_x, stick_y)
        stick_vector = stick_vector.normalize()
        direction += stick_vector

    if direction or movement:
        movement = movement * air_resistance
        if direction:
            direction = direction.normalize() * acceleration
            movement += direction
        if movement.magnitude() > max_speed:
            movement.scale_to_length(max_speed)
        circle.pos += movement
        sword_and_shield.pos = circle.pos

    def update_shield(angle):
        # hooray, wasabi2d uses radians and pygame uses degrees
        angle = (angle * math.tau) / 360
        if abs(sword_and_shield.angle - angle) <= max_shield_delta:
            sword_and_shield.angle = angle
        elif angle < sword_and_shield.angle:
            sword_and_shield.angle -= max_shield_delta
        else:
            sword_and_shield.angle += max_shield_delta

    mouse_movement = pygame.mouse.get_rel()
    if mouse_movement[0] or mouse_movement[1]:
        mouse_vector = Vector2(mouse_movement)
        mouse_polar = mouse_vector.as_polar()
        print("mouse", mouse_vector, mouse_polar)
        update_shield(mouse_polar[1])

    stick_rx = stick.get_axis(3)
    stick_ry = stick.get_axis(4)
    # print(stick.get_axis(2), stick.get_axis(3), stick.get_axis(4), stick.get_axis(5))
    if stick_rx or stick_ry:
        joy_vector = Vector2(stick_rx, stick_ry)
        joy_polar = joy_vector.as_polar()
        print("joy", joy_vector, joy_polar)
        update_shield(joy_polar[1])


print("AXES", stick.get_numaxes())


clock.schedule_interval(move_winky, 0.05)

run()  # keep this at the end of the file
