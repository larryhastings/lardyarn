import enum


class CollisionType(enum.IntEnum):
    NONE = 0
    WALL = 1
    PLAYER = 2
    ZONE = 3


class Layers(enum.IntEnum):
    FLOOR = -1
    DEBRIS = 0
    WALL = 1
    LOWER_EFFECTS = 2
    UPPER_EFFECTS = 3
    ENTITIES = 4
    UPPER_ENTITIES = 5
    BULLETS = 6
    ZONE = 7
    HUD = 8
    TEXTBG = 9
    TEXT = 10

