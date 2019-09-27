#!/usr/bin/env python3
from vector2d import Vector2D


def polygon_collision(poly, circle):
    edges = zip(poly, poly[1:] + poly[:1])
    for i, (a, b) in enumerate(edges):
        along_x, along_y = (b - a).normalized()
        across = Vector2D(-along_y, along_x)
        off = across.dot(a)

        if across.dot(circle.pos) < off - circle.radius:
            return False
    return True


if __name__ == "__main__":

    from wasabi2d import Scene, event, run, keys
    from pygame import joystick

    scene = Scene()

    triangle = [
        Vector2D(100, 400),
        Vector2D(300, 500),
        Vector2D(200, 600)
    ]

    scene.layers[0].add_polygon(triangle, fill=False, color='yellow')
    circ = scene.layers[0].add_circle(radius=20, fill=False, color='red')

    @event
    def on_mouse_move(pos):
        circ.pos = pos
        circ.color = 'red' if polygon_collision(triangle, circ) else 'green'

    run()
