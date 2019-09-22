import numpy as np
import math
from wasabi2d import Scene, event, run, Vector2


scene = Scene(title="Ascent - PyWeek 28")


class Knight:
    """The player character."""

    def __init__(self):
        self.shield = scene.layers[0].add_sprite('shield')
        self.sword = scene.layers[0].add_sprite('sword')
        self.rhand = scene.layers[0].add_sprite('rhand')
        self.knight = scene.layers[0].add_sprite('knight')

        self.pos = Vector2(scene.width, scene.height) * 0.5
        self.v = Vector2()
        self.accel = Vector2()

        self.shield_angle = 0

    def accelerate(self, v):
        self.accel += Vector2(v)

    # Acceleration of the knight in pixels/s^2
    ACCELERATION = 400

    def update(self, dt):
        """Update the knight this frame."""
        self.v *= 0.1 ** dt   # drag

        if self.accel:
            # New acceleration this frame
            self.v += self.ACCELERATION * self.accel.normalize() * dt

        dv, angle = self.v.as_polar()
        if dv > 1e-2:
            self.knight.angle = math.radians(angle)

        self.pos += knight.v * dt
        self.knight.pos = self.pos
        self._update_shield()
        self.accel *= 0.0

    @property
    def shield_angle(self):
        """Get the angle of the shield."""
        return self.shield.angle

    @shield_angle.setter
    def shield_angle(self, v):
        self.shield.angle = v
        self._update_shield()

    def _update_shield(self):
        v = self.shield.angle
        c = np.sin(v)
        s = np.cos(v)

        self.shield.pos = self.knight.pos + np.array([s, c]) * 40

    def delete(self):
        self.knight.delete()
        self.shield.delete()
        self.sword.delete()
        self.rhand.delete()



knight = Knight()


@event
def update(dt, keyboard):
    if keyboard.left:
        knight.accelerate((-1, 0))
    elif keyboard.right:
        knight.accelerate((1, 0))

    if keyboard.up:
        knight.accelerate((0, -1))
    elif keyboard.down:
        knight.accelerate((0, 1))

    knight.update(dt)


run()
