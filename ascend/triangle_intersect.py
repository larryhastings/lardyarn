#!/usr/bin/env python3
from .vector2d import Vector2D
import numpy as np


def polygon_collision(poly, circle_pos, circle_radius):
    edges = zip(poly, poly[1:] + poly[:1])
    pen_depth = np.inf
    pen = None
    depths = []
    for i, (a, b) in enumerate(edges):
        along_x, along_y = (b - a).normalized()
        across = Vector2D(-along_y, along_x)
        off = across.dot(a)

        depth = across.dot(circle_pos) - off + circle_radius
        depths.append(depth)
        if depth < 0:
            return None
        if depth < pen_depth:
            pen_depth = depth
            pen = across * depth
    points = np.array(poly)

    relpts = points - circle_pos
    dists = np.hypot(relpts[:, 0], relpts[:, 1])

    closest = np.argmin(dists, axis=0)
    close_point = relpts[closest]

    if dists[closest] < 1e-5:
        return pen

    to_corner = close_point / np.linalg.norm(close_point)
    dists = np.dot(relpts, to_corner)
    if np.all(dists >= closest - 1e-5):
        if dists[closest] > circle_radius:
            return None
        else:
            return Vector2D(*to_corner * (circle_radius - dists[closest]))

    return pen

if __name__ == "__main__":
    from wasabi2d import Scene, event, run, keys
    from pygame import joystick

    scene = Scene()
    scene.background = (0.2,) * 3
    scene.layers[0].set_effect('dropshadow', radius=1)

    triangle = [
        Vector2D(100, 200),
        Vector2D(300, 300),
        Vector2D(200, 400)
    ]

    scene.layers[0].add_polygon(triangle, fill=False, color='yellow')
    circ = scene.layers[0].add_circle(radius=20, fill=False, color='red')

    @event
    def on_mouse_move(pos):
        circ.pos = pos
        pen = polygon_collision(triangle, pos, circ.radius)

        if pen:
            circ.pos -= pen
        circ.color = 'red' if pen else 'green'

    run()
