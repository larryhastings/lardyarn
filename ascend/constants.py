import enum

class CollisionType(enum.IntEnum):
    NO_COLLISION = 0
    COLLISION_WITH_WALL = 1
    COLLISION_WITH_PLAYER = 2
    COLLISION_WITH_ZONE = 3

class Layers(enum.IntEnum):
    DEBRIS_LAYER = 0
    WALL_LAYER = 1
    LOWER_EFFECTS_LAYER = 2
    UPPER_EFFECTS_LAYER = 3
    ENTITIES_LAYER = 4
    BULLETS_LAYER = 5
    ZONE_LAYER = 6
    TEXT_LAYER = 7

