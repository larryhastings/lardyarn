import math
import random
import numpy as np

from wasabi2d import Vector2, animate, clock, sounds
from .constants import Layers, CollisionType
from .vector2d import Vector2D, Polar2D



class MagicMissile:
    SMOKE_RATE = 20
    SPEED = 200
    SPIN = 0.5

    def __init__(self, world, pos, vel):
        self.world = world
        self.scene = world.scene
        self.vel = vel
        self.sprite = self.scene.layers[0].add_sprite(
            'spark',
            pos=pos,
        )
        self.sprite.color = (0.4, 3.0, 0.4, 1.0)
        self.sprite.scale = 0.3
        self.age = 0

    @property
    def pos(self):
        return self.sprite.pos

    @pos.setter
    def pos(self, v):
        self.sprite.pos = v

    def update(self, dt):
        self.scene.smoke.emit(
            num=np.random.poisson(self.SMOKE_RATE * dt),
            pos=self.sprite.pos,
            vel_spread=10,
            spin_spread=1,
            size=6,
            size_spread=3,
            angle_spread=3,
            color=(0, 1, 0, 1.0),
        )
        self.scene.sparks.emit(
            num=np.random.poisson(self.SMOKE_RATE * dt),
            pos=self.sprite.pos,
            vel=self.vel * 0.8,
            vel_spread=30,
            spin_spread=1,
            size=4,
            angle_spread=3,
            color=(0.2, 1, 0.2, 1),
        )

    def delete(self):
        """Remove the missile from the world."""
        self.world.objects.remove(self)
        self.sprite.delete()

    def hit(self):
        """Kill the missile, showing an effect like it hit something."""
        pos = self.sprite.pos

        self.scene.smoke.emit(
            num=25,
            pos=pos,
            vel=-0.4 * self.vel,
            vel_spread=50,
            spin_spread=1,
            size=6,
            size_spread=3,
            angle_spread=3,
            color=(0, 2, 0, 1.0),
        )
        self.delete()


class TimedMagicMissile(MagicMissile):
    EXPLODE_TIME = 1

    def update(self, dt):
        super().update(dt)

        self.sprite.pos += self.vel * dt
        self.sprite.angle += self.SPIN * dt

        self.age += dt
        if self.age > self.EXPLODE_TIME:
            self.hit()
            return


class Skeleton:
    radius = 12

    def __init__(self, world, pos, angle=0):
        self.world = world
        scene = self.scene = world.scene

        self.body = scene.layers[0].add_sprite(
            'skeleton-body',
            pos=pos,
            angle=angle
        )
        self.body_animate = None
        self.head = scene.layers[0].add_sprite(
            'skeleton-head',
            pos=pos,
            angle=angle
        )

        self.target = random.choice(world.pcs) if world.pcs else None
        self.bob = 1.0
        self.gait_speed = random.uniform(0.3, 0.5)
        self.gait_step = random.uniform(1.07, 1.2)

    SPEED = 30

    @property
    def pos(self):
        return Vector2(*self.head.pos)

    @pos.setter
    def pos(self, v):
        self.head.pos = self.body.pos = v

    def update(self, dt):
        to_target = Vector2(*self.target.pos - self.head.pos)
        dist, angle_deg = to_target.as_polar()
        angle_to_target = math.radians(angle_deg)
        self.head.angle = angle_to_target

        if dist > 30:
            self.head.pos += to_target.normalize() * self.SPEED * dt
            self.body.pos = self.head.pos
            self.bob += self.gait_speed * dt
            if self.bob > self.gait_step:
                self.bob = 1.0
            self.head.scale = self.bob
            self.body.scale = 1 + 0.5 * (self.bob - 1.0)

        self.body_animate = animate(
            self.body, duration=0.3, angle=angle_to_target
        )

    def delete(self):
        self.head.delete()
        self.body.delete()
        if self.body_animate:
            self.body_animate.stop()

    def die(self, vel=(0, 0)):
        self.delete()
        self.scene.bones.emit(
            10,
            pos=self.pos,
            vel=vel,
            vel_spread=80,
            spin_spread=3,
            size=6,
            size_spread=1,
            angle_spread=6,
        )
        self.scene.skulls.emit(
            1,
            pos=self.pos,
            vel=vel,
            vel_spread=80,
            spin_spread=1,
            size=8,
        )


class Mage(Skeleton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        clock.schedule(self.fire, random.randrange(30))

    def fire(self):
        """Fire a magic missile at the player."""
        pos = self.pos
        aim = Vector2(*self.target.pos) - pos

        self.world.objects.append(
            TimedMagicMissile(
                self.world,
                pos,
                aim.normalize() * MagicMissile.SPEED
            )
        )


def repr_float(f):
    return f"{f:4.3f}"


bad_guy_id = 1

class BadGuy:
    die_on_any_collision = False

    def __init__(self, world):
        self.world = world
        self.game = world.game

        global bad_guy_id
        self.pos = Vector2D()
        self.id = bad_guy_id
        bad_guy_id += 1
        self.radius_squared = self.radius ** 2
        self.outer_collision_distance = (self.radius + world.player.outer_radius)
        self.outer_collision_distance_squared = self.outer_collision_distance ** 2
        self.body_collision_distance = (self.radius + world.player.body_radius)
        self.body_collision_distance_squared = self.body_collision_distance ** 2
        self.zone_collision_distance = (self.radius + world.player.zone_radius)
        self.zone_collision_distance_squared = self.zone_collision_distance ** 2

    def _close(self):
        self.dead = True
        self.shape.delete()

    def close(self):
        self.world.enemies.remove(self)
        self._close()

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.id} ({repr_float(self.pos.x)}, {repr_float(self.pos.y)})>"

    min_random_distance = 150
    min_random_distance_squared = min_random_distance ** 2
    random_placement_inset = 20
    def random_placement(self):
        world = self.world
        while True:
            offset = self.random_placement_inset
            self.pos = Vector2D(
                random.randint(offset, world.scene.width - offset),
                random.randint(offset, world.scene.height - offset))

            # don't go near the player
            delta = world.player.pos - self.pos
            if delta.magnitude_squared < self.min_random_distance_squared:
                continue

            # don't intersect with any walls
            if self.world.detect_wall_collisions(self):
                continue

            break

    speed = 1
    radius = 1
    dead = False

    def move_to(self, v):
        # print(f"{time:8}", self, "move to", v)
        self.shape.pos = self.pos = v
        player = self.world.player

        collision = player.compute_collision_with_bad_guy(self)

        if collision == CollisionType.COLLISION_WITH_ZONE:
            player.on_collision_zone(self)
            self.on_collide_zone()
        elif collision == CollisionType.COLLISION_WITH_PLAYER:
            player.on_collision_body(self)
            self.on_collide_player()
        else:
            penetration_vector = self.world.detect_wall_collisions(self)
            if penetration_vector:
                if self.die_on_any_collision:
                    self.close()
                    return
                self.pos -= penetration_vector
                self.shape.pos = self.pos


    def move_delta(self, delta):
        v = self.pos + delta
        self.move_to(v)

    def move_towards_player(self):
        player = self.world.player
        delta = player.pos - self.pos
        if delta.magnitude > self.speed:
            delta = delta.scaled(self.speed)
        self.move_to(self.pos + delta)

    def push_away_from_player(self):
        player = self.world.player
        delta = self.pos - player.pos
        delta2 = delta.scaled(self.body_collision_distance * 1.2)
        # print(f"push away self.pos {self.pos} player.pos {player.pos} delta {delta} delta2 {delta2}")
        self.move_to(player.pos + delta2)

    def on_collide_player(self):
        pass

    # def on_collide_shield(self):
    #     self.push_away_from_player()

    def on_collide_zone(self):
        self.on_death()

    def on_death(self):
        self.close()



class Stalker(BadGuy):
    radius = 10

    def move_towards_spot(self):
        player = self.world.player
        pos = player.pos + self.spot_offset
        delta = pos - self.pos
        if delta.magnitude > self.speed:
            delta = delta.scaled(self.speed)
        self.move_to(self.pos + delta)

    def __init__(self, world, fast):
        super().__init__(world)
        if fast:
            self.speed = 1.75
            color = (1, 0.75, 0)
        else:
            self.speed = 0.8
            color = (0.8, 0.3, 0.3)

        self.shape = Skeleton(self.world, Vector2D(0, 0))
#        scene.layers[Layers.ENTITIES_LAYER].add_star(
#            outer_radius=self.radius,
#            inner_radius=4,
#            points = 6,
#            color=color,
#            )
        self.random_placement()
        self.spot_high_watermark = 140
        self.spot_low_watermark = 90
        self.spot_radius_min = 30
        self.spot_radius_max = 70
        self.spot_offset = Vector2D(random.randint(self.spot_radius_min, self.spot_radius_max), 0).rotated(random.randint(0, 360))
        self.head_to_spot = True

    def update(self, dt):
        if self.dead:
            return

        # Stalkers pick a random spot near the player
        #
        # they move towards that spot until they get "close enough" to the player
        # at which point they head directly towards the player
        #
        # until they get "too far" from the player,
        # at which point they start moving towards the random spot again.
        player = self.world.player
        delta = player.pos - self.pos
        distance_to_player = delta.magnitude

        threshold = self.spot_low_watermark if self.head_to_spot else self.spot_high_watermark
        self.head_to_spot = distance_to_player > threshold

        if self.head_to_spot:
            self.move_towards_spot()
        else:
            self.move_towards_player()

    def _close(self):
        self.shape.die(Vector2D())


class Shot(BadGuy):
    radius = 2
    speed = 4
    lifetime = 2
    die_on_any_collision = True

    def __init__(self, shooter):
        super().__init__(shooter.world)
        player = self.world.player
        self.shooter = shooter
        self.pos = Vector2D(shooter.shape.pos[0], shooter.shape.pos[1])
        self.delta = (player.pos - self.pos).scaled(self.speed)
        self.shape = MagicMissile(self.world, self.pos, self.delta)
        self.world.objects.append(self.shape)
        self.expiration_date = self.game.time + self.lifetime
        sounds.enemy_shot.play()

    def update(self, dt):
        if self.dead:
            return
        if self.game.time > self.expiration_date:
            self.on_death()
            return
        self.move_delta(self.delta)

    def on_collide_shield(self):
        self.remove()

    def _close(self):
        self.shape.hit()



class Shooter(BadGuy):
    min_time = 0.5
    max_time = 1.5

    speed = 0.3
    radius = 8

    def __init__(self, world):
        super().__init__(world)
        self.shape = world.scene.layers[Layers.ENTITIES_LAYER].add_circle(
            radius=self.radius,
            color=(1/2, 0, 1),
            )
        self.random_placement()

        self._next_shot_time()

    def _next_shot_time(self):
        self.next_shot_time = self.world.game.time + self.min_time + (random.random() * (self.max_time - self.min_time))

    def shoot(self):
        # print("shoot!", self)
        shot = Shot(self)
        self.world.enemies.append(shot)
        self._next_shot_time()

    def update(self, dt):
        if self.dead:
            return
        self.move_towards_player()
        if self.world.game.time >= self.next_shot_time:
            self.shoot()

