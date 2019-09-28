import enum

class CollisionType(enum.IntEnum):
    NONE = 0
    WALL = 1
    PLAYER = 2
    ZONE = 3


class Layers(enum.IntEnum):
    DEBRIS = 0
    WALL = 1
    LOWER_EFFECTS = 2
    UPPER_EFFECTS = 3
    ENTITIES = 4
    BULLETS = 5
    ZONE = 6
    TEXTBG = 8
    TEXT = 9

