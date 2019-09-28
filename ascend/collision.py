from .vector2d import Vector2D, Polar2D
from .triangle_intersect import polygon_collision

def entity_collision(
    entity1,
    entity2,
    ):

    delta = entity1.pos - entity2.pos
    return delta.magnitude_squared < (entity1.radius_squared + entity2.radius_squared)



def circle_rect_collision(
    circle_pos: Vector2D,
    circle_radius_squared: float,

    upper_left: Vector2D,
    lower_right: Vector2D):

    x, y = circle_pos

    if x < upper_left.x:
        x = upper_left.x
    elif x > lower_right.x:
        x = lower_right.x

    if y < upper_left.y:
        y = upper_left.y
    elif y > lower_right.y:
        y = lower_right.y

    delta = circle_pos - Vector2D(x, y)
    return delta.magnitude_squared <= circle_radius_squared
