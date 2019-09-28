import sys
import numpy as np
import atexit
import json
from wasabi2d import Scene, event, run, keys, Vector2
from ascend.triangle_intersect import polygon_collision
from pygame import joystick
from scipy.spatial import ConvexHull


file = sys.argv[1]
datafile = file + '-walls.json'
scene = Scene(rootdir='ascend', width=350, height=720)
scene.background = (0.2,) * 3

for suffix in ('-floor', '-wall'):
    scene.layers[-1].add_sprite(
        file + suffix,
        pos=(scene.width / 2, scene.height / 2)
    )
scene.layers[0].set_effect('dropshadow', radius=1)


def convex_hull(points):
    return points[ConvexHull(points).vertices].copy()


class Poly:
    def __init__(self):
        self.points = np.zeros((0, 2))
        self.handles = []
        self.shape = None

    def add_point(self, pos):
        self.points = np.vstack([self.points, [pos]])
        self._rebuild()
        self._add_handle(pos)

    def _add_handle(self, pos):
        self.handles.append(
            scene.layers[1].add_rect(4, 4, pos=pos)
        )

    def reduce(self):
        if len(self.points) > 2:
            self.points = convex_hull(self.points)
            self._rebuild()

            for h in self.handles:
                h.delete()
            self.handles.clear()
            for p in self.points:
                self._add_handle(p)

    def _rebuild(self):
        if self.shape:
            self.shape.delete()

        if len(self.points) > 2:
            self.shape = scene.layers[0].add_polygon(
                convex_hull(self.points),
                color='red',
                fill=False
            )

    def move_point(self, idx, pos):
        self.points[idx] = pos
        self.handles[idx].pos = pos
        self._rebuild()

    def show_handles(self, show):
        for h in self.handles:
            if show:
                h.color = 'white'
            else:
                h.color = '#00000000'

    def __len__(self):
        return len(self.points)

    def contains(self, p):
        return polygon_collision(self.points, p, 0) is not None

    def delete(self):
        if len(self.points) < 3:
            polys.remove(self)
        if self.shape:
            self.shape.delete()
        for h in self.handles:
            h.delete()


def load():
    global current_poly
    global polys
    try:
        with open(datafile) as f:
            pts = json.load(f)
        polys = []
        for loop in pts:
            poly = Poly()
            for point in loop:
                poly.add_point(point)
            polys.append(poly)
        if polys:
            current_poly = polys[-1]
            return
    except IOError:
        pass
    current_poly = Poly()
    polys = [current_poly]


current_poly = None
polys = None
load()


def set_current_poly(p):
    global current_poly
    if len(current_poly) < 3:
        current_poly.delete()
    current_poly = p
    for poly in polys:
        if poly.shape:
            poly.shape.color = 'red' if poly is current_poly else '#cccccc'
        poly.show_handles(poly is current_poly)


@event
def on_mouse_down(pos):
    global current_poly
    global current_point
    if current_poly and len(current_poly) < 3:
        current_poly.add_point(pos)
        current_point = len(current_poly) - 1
        return
    for p in polys:
        if p.contains(pos):
            set_current_poly(p)
            current_point = None
            return
    else:
        if current_poly:
            current_poly.add_point(pos)
            current_point = len(current_poly) - 1


@event
def on_mouse_up(pos):
    global current_point
    if current_poly:
        current_poly.reduce()
        current_point = None


@event
def on_mouse_move(pos, buttons):
    if not buttons:
        return

    if current_point:
        current_poly.move_point(current_point, pos)


@event
def on_key_down(key):
    if key == keys.RETURN:
        p = Poly()
        polys.append(p)
        set_current_poly(p)
    elif key == keys.TAB:
        idx = polys.index(current_poly)
        idx = (idx + 1) % len(polys)
        set_current_poly(polys[idx])


@atexit.register
def on_exit():
    pts = []
    for poly in polys:
        poly.reduce()
        if len(poly) > 2:
            pts.append([tuple(p) for p in poly.points])

    with open(datafile, 'w') as f:
        json.dump(pts, f)
    print("Wrote", datafile)


run()
