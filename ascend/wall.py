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
    def __init__(self, level, upper_left, lower_right, visible=True):
        global wall_id
        self.id = wall_id
        wall_id += 1

        self.level = level
        self.upper_left = upper_left
        self.lower_right = lower_right
        self.width = lower_right.x - upper_left.x
        self.height = lower_right.y - upper_left.y
        self.pos = Vector2D(upper_left.x + (self.width / 2), upper_left.y + (self.height / 2))
        # print(f"WALL ul {upper_left} lr {lower_right} pos {self.pos} wxh {self.width} {self.height}")

        self.collision_edges = [
            upper_left,
            Vector2D(lower_right.x, upper_left.y),
            lower_right,
            Vector2D(upper_left.x, lower_right.y),
            ]

        if visible:
            self.layer = level.scene.layers[Layers.ENTITIES]
            self.shape = self.layer.add_rect(
                pos=self.pos,
                width=self.width,
                height=self.height,
                color=(0.25, 0.25, 0.25),
                fill = True,
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
        if circle_rect_collision(
            entity.pos, entity.radius_squared,
            self.upper_left,
            self.lower_right):
            return polygon_collision(self.collision_edges, entity.pos, entity.radius)
        return None

