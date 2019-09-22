import sys
import math
import wasabi2d
from wasabi2d import Scene, run, event, clock, Vector2, keys
import pygame.mouse
from pygame import joystick


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


@event
def update(dt, keyboard):
    global movement
    global shield_angle

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

    circle.pos += movement * dt
    sword_and_shield.pos = circle.pos

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



run()  # keep this at the end of the file
