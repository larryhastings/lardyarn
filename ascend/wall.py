import numpy as np
from pygame import Rect

from .vector2d import Vector2D, Polar2D
from .collision import circle_rect_collision, polygon_collision
from .constants import Layers

def repr_float(f):
    return f"{f:4.3f}"


wall_id = 1

class Wall:
    # remember that in Wasabi2d (0, 0) is in the upper-left.
    # x grows as we move right.
    # y grows as we move down.

    @classmethod
    def rect(cls, level, upper_left, lower_right, visible=True):
        level = level
        upper_left = upper_left
        lower_right = lower_right

        points = [
            upper_left,
            Vector2D(lower_right.x, upper_left.y),
            lower_right,
            Vector2D(upper_left.x, lower_right.y),
        ]
        return cls(level, points, visible)

    def __init__(self, level, points, visible=True):
        global wall_id
        self.id = wall_id
        wall_id += 1

        self.points = points
        self.upper_left = Vector2D(np.min(self.points, axis=0))
        self.lower_right = Vector2D(np.max(self.points, axis=0))
        self.r = Rect(
            *self.upper_left - Vector2D(50, 50),
            *self.lower_right - self.upper_left + Vector2D(100, 100)
        )

        if visible:
            self.layer = level.scene.layers[Layers.ENTITIES]
            self.shape = self.layer.add_polygon(
                points,
                color=(0.25, 0.25, 0.25),
                fill=True,
            )
        else:
            self.shape = self.layer = None

    def __repr__(self):
        return f"<Wall {self.id} ({repr_float(self.upper_left.x)}, {repr_float(self.upper_left.y)} x ({repr_float(self.lower_right.x)}, {repr_float(self.lower_right.y)}>"

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
        if not self.r.collidepoint(entity.pos):
            return None
        return polygon_collision(self.points, entity.pos, entity.radius)

