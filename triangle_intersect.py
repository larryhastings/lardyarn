#!/usr/bin/env python3
from wasabi2d import Vector2


def polygon_collision(poly, circle):
    edges = zip(poly, poly[1:] + poly[:1])
    for i, (a, b) in enumerate(edges):
        along_x, along_y = (b - a).normalize()
        across = Vector2(-along_y, along_x)
        off = across.dot(a)

        if across.dot(circle.pos) < off - circle.radius:
            return False
    return True


if __name__ == "__main__":

    from wasabi2d import Scene, event, run, keys, Vector2
    from pygame import joystick

    scene = Scene()

    triangle = [
        Vector2(100, 400),
        Vector2(300, 500),
        Vector2(200, 600)
    ]

    scene.layers[0].add_polygon(triangle, fill=False, color='yellow')
    circ = scene.layers[0].add_circle(radius=20, fill=False, color='red')

    @event
    def on_mouse_move(pos):
        circ.pos = pos
        circ.color = 'red' if polygon_collision(triangle, circ) else 'green'

    run()
