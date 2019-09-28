import math
import random
import numpy as np

from wasabi2d import Vector2, animate, clock, sounds
from .constants import Layers, CollisionType
from .vector2d import Vector2D, Polar2D
from .collision import entity_collision


class MagicMissile:
    SMOKE_RATE = 20
    SPEED = 200
    SPIN = 0.5

    def __init__(self, level, pos, vel):
        self.level = level
        self.scene = level.scene
        self.vel = vel
        self.sprite = self.scene.layers[Layers.UPPER_EFFECTS].add_sprite(
            'spark',
            pos=pos,
        )
        self.sprite.color = (0.4, 2.0, 0.4, 1.0)
        self.sprite.scale = 0.3
        self.age = 0
        self.level.objects.append(self)
        clock.each_tick(self.update)

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

    deleted = False
    def delete(self):
        """Remove the missile from the level."""
        if not self.deleted:
            self.deleted = True
            clock.unschedule(self.update)
            self.level.objects.remove(self)
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


class BombPowerup:
    def __init__(self, level: 'ascend.level.Level', pos):
        self.level = level
        scene = level.scene
        self.sprite = scene.layers[Layers.LOWER_EFFECTS].add_sprite(
            'bomb-up',
            pos=pos
        )
        self.vel = Vector2D(
            random.uniform(-100, 100),
            random.uniform(-100, 100),
        )
        self.collectable = False
        level.objects.append(self)
        clock.schedule(self.blink_on, 0.5)

    def blink_on(self):
        self.collectable = True
        self.sprite.color = (2, 2, 2, 1)
        clock.schedule(self.blink_off, 0.1)

    def blink_off(self):
        self.sprite.color = 'white'
        clock.schedule(self.blink_on, 0.5)

    def update(self, dt):
        self.vel *= 0.2 ** dt
        self.sprite.pos += self.vel * dt

        player = self.level.player
        if self.collectable and (player.pos - self.sprite.pos).magnitude < 30:
            self.delete()
            player.add_bomb()

    def delete(self):
        self.sprite.delete()
        self.sprite = None
        self.level.objects.remove(self)


class Skeleton:
    radius = 12

    def __init__(self, level, pos, angle=0):
        self.level = level
        scene = self.scene = level.scene

        self.body = scene.layers[Layers.ENTITIES].add_sprite(
            'skeleton-body',
            pos=pos,
            angle=angle
        )
        self.body_animate = None
        self.head = scene.layers[Layers.ENTITIES].add_sprite(
            'skeleton-head',
            pos=pos,
            angle=angle
        )

        self.target = random.choice(level.pcs) if level.pcs else None
        self.t = 0
        self.bob = 1.0
        self.last_pos = Vector2D()
        self.gait_speed = random.uniform(0.007, 0.009)
        self.gait_step = random.uniform(1.07, 1.2)
        clock.each_tick(self.update)

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

        cur_pos = Vector2D(self.head.pos)
        dist = (cur_pos - self.last_pos).magnitude
        self.last_pos = cur_pos

        self.t += dist * self.gait_speed

        self.bob += self.gait_speed * dist
        if self.bob > self.gait_step:
            self.bob = 1.0
        self.head.scale = self.body.scale = self.bob
        self.body.angle = angle_to_target + 0.1 * np.sin(self.t * 50)

    def delete(self):
        clock.unschedule(self.update)
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
            size=7,
        )
        if random.randrange(10) == 0:
            BombPowerup(self.level, self.pos)


class Mage(Skeleton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        clock.schedule(self.fire, random.randrange(30))

    def fire(self):
        """Fire a magic missile at the player."""
        pos = self.pos
        aim = Vector2(*self.target.pos) - pos

        self.level.objects.append(
            TimedMagicMissile(
                self.level,
                pos,
                aim.normalize() * MagicMissile.SPEED
            )
        )


def repr_float(f):
    return f"{f:4.3f}"


entity_id = 1

class Entity:
    shape = None

    def __init__(self, level):
        self.level = level
        self.game = level.game

        global entity_id
        self.pos = Vector2D()
        self.id = entity_id
        entity_id += 1
        self.radius_squared = self.radius ** 2
        self.outer_collision_distance = (self.radius + level.player.outer_radius)
        self.outer_collision_distance_squared = self.outer_collision_distance ** 2
        self.body_collision_distance = (self.radius + level.player.body_radius)
        self.body_collision_distance_squared = self.body_collision_distance ** 2
        self.zone_collision_distance = (self.radius + level.player.zone_radius)
        self.zone_collision_distance_squared = self.zone_collision_distance ** 2

    def delete(self):
        self.level.enemies.remove(self)
        self.dead = True
        if self.shape:
            self.shape.delete()


class BadGuy(Entity):
    die_on_any_collision = False

    def init_spot(self):
        # pick a random spot near the player
        #
        # move towards that spot until you get "close enough" to the player,
        # at which point head directly towards the player.
        #
        # until they get "too far" from the player,
        # at which point start moving towards the spot again.
        self.spot_high_watermark = 140
        self.spot_low_watermark = 90
        self.spot_radius_min = 30
        self.spot_radius_max = 70
        self.spot_offset = Vector2D(random.randint(self.spot_radius_min, self.spot_radius_max), 0).rotated(random.randint(0, 360))
        self.head_to_spot = True

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.id} ({repr_float(self.pos.x)}, {repr_float(self.pos.y)})>"

    min_random_distance = 150
    min_random_distance_squared = min_random_distance ** 2
    random_placement_inset = 20
    def random_placement(self):
        level = self.level
        while True:
            offset = self.random_placement_inset
            self.pos = Vector2D(
                random.randint(offset, level.scene.width - offset),
                random.randint(offset, level.scene.height - offset))

            # don't go near the player
            delta = level.player.pos - self.pos
            if delta.magnitude_squared < self.min_random_distance_squared:
                continue

            # don't intersect with any walls
            if self.level.detect_wall_collisions(self):
                continue

            break
        self.shape.pos = self.pos

    speed = 1
    radius = 1
    dead = False

    def move_to(self, v):
        # print(f"{time:8}", self, "move to", v)
        self.shape.pos = self.pos = v

    def move_delta(self, delta):
        v = self.pos + delta
        self.move_to(v)

    def move_towards_pos(self, pos):
        delta = pos - self.pos
        if delta.magnitude > self.speed:
            delta = delta.scaled(self.speed)
        self.move_to(self.pos + delta)

    def move_towards_player(self):
        return self.move_towards_pos(self.level.player.pos)

    def move_towards_spot(self):
        player = self.level.player
        delta = player.pos - self.pos
        distance_to_player = delta.magnitude

        threshold = self.spot_low_watermark if self.head_to_spot else self.spot_high_watermark
        self.head_to_spot = distance_to_player > threshold

        pos = player.pos
        if self.head_to_spot:
            pos += self.spot_offset
        self.move_towards_pos(pos)

    def push_away_from_entity(self, entity):
        delta = self.pos - entity.pos
        if not delta.magnitude_squared:
            delta = Vector2D(0, 1)
        delta2 = delta.scaled(self.body_collision_distance * 1.2)
        # print(f"push away self.pos {self.pos} player.pos {player.pos} delta {delta} delta2 {delta2}")
        self.move_to(entity.pos + delta2)

    def on_collide_player(self):
        pass

    # def on_collide_shield(self):
    #     self.push_away_from_player()

    def on_collide_zone(self):
        self.on_death()

    def die(self, v):
        self.on_death()

    def on_death(self):
        self.delete()



class Stalker(BadGuy):
    radius = 10

    def __init__(self, level, fast, *, pos=None):
        super().__init__(level)
        if fast:
            self.speed = 1.75
            #color = (1, 0.75, 0)
        else:
            self.speed = 0.8
            #color = (0.8, 0.3, 0.3)

        self._mkshape()
        if pos is None:
            self.random_placement()
        else:
            self.pos = self.shape.pos = pos
        self.init_spot()

    def _mkshape(self):
        self.shape = Skeleton(self.level, Vector2D(0, 0))

    def delete(self):
        super().delete()
        self.shape.die(Vector2D())

    def update(self, dt):
        if self.dead:
            return
        self.move_towards_spot()


class Blobby:
    def __init__(self, scene, pos=Vector2D(), radius=20):
        self.scene = scene
        layer = scene.layers[Layers.ENTITIES]
        self.shape = layer.add_sprite('blob')
        self.shape.angle = random.uniform(-1, 1)
        self.radius = radius

        self.bounciness = Vector2D(1.1, 0.9)
        self.shape.pos = pos
        self.squish_x = random.choice([True, False])
        self.bounce()
        clock.schedule_interval(self.bounce, 0.5)

    @property
    def pos(self):
        return self.shape.pos

    @pos.setter
    def pos(self, v):
        self.shape.pos = v

    @property
    def radius(self):
        return self._radius

    @radius.setter
    def radius(self, v):
        self._radius = v

    def bounce(self):
        self.squish_x = not self.squish_x
        x, y = self.bounciness * (self._radius / 20)
        if self.squish_x:
            x, y = y, x
        self.anim = animate(
            self.shape,
            'accel_decel',
            duration=0.5,
            scale_x=x,
            scale_y=y,
        )

    def delete(self):
        self.anim.stop()
        clock.unschedule(self.bounce)
        self.shape.delete()

    def die(self, vel=Vector2D()):
        self.scene.smoke.emit(
            num=self.radius,
            pos=self.shape.pos,
            vel=-0.4 * vel,
            vel_spread=5 * self.radius,
            spin_spread=1,
            size=3 * (self.radius / 10),
            size_spread=3,
            angle_spread=3,
            color='#cc00ccff'
        )
        self.delete()


class StalkerBlob(Stalker):
    def _mkshape(self):
        self.shape = Blobby(self.game.scene, radius=self.radius)


class Splitter(BadGuy):
    radius = 20

    def __init__(self, level):
        super().__init__(level)
        self.speed = 1.3

        self.shape = Blobby(self.game.scene, radius=self.radius)
        self.random_placement()
        self.init_spot()

    def delete(self):
        self.shape.die()
        self.shape = None
        if self.level.player:
            # game over
            delta = Polar2D(self.pos - self.level.player.pos)
            for i in range(2):
                delta = Polar2D(60, delta.theta + math.tau / 3)
                self.level.enemies.append(
                    StalkerBlob(self.level, pos=self.pos + delta, fast=True)
                )

        super().delete()

    def update(self, dt):
        if self.dead:
            return
        self.move_towards_spot()


class Bloblet(BadGuy):
    _radius = 15

    def __init__(self, level, leader):
        super().__init__(level)
        self.shape = Blobby(level.scene, radius=self._radius)
        self.radius = 15

        if leader:
            self.init_follower(leader)
        else:
            self.init_leader()

        self.random_placement()

    @property
    def radius(self):
        return self._radius

    @radius.setter
    def radius(self, v):
        self.shape.radius = self._radius = v

    def init_leader(self):
        self.leader = None
        animate(self, radius=30)
        self.speed = 0.8
        self.blobs = set((self,))

    def init_follower(self, leader):
        self.leader = leader
        self.speed = 2.5
        leader.blobs.add(self)

    def delete(self):
        if self.leader:
            self.leader.blobs.remove(self)
        else:
            self.blobs.discard(self)
            if self.blobs:
                new_leader = None
                min_distance_squared = 50000000
                for blob in self.blobs:
                    delta = self.pos - blob.pos
                    distance_squared = delta.magnitude_squared
                    if min_distance_squared > distance_squared:
                        min_distance_squared = distance_squared
                        new_leader = blob
                assert new_leader
                new_leader.init_leader()
                new_leader.blobs = self.blobs
                for blob in self.blobs:
                    blob.leader = new_leader
                # new_leader is in self.blobs!
                new_leader.leader = None
            self.blobs = None
        super().delete()

    def update(self, dt):
        if self.dead:
            return

        # print(f"{self.level.game.time} MOVING BLOB", self, end=" ")
        if not self.leader:
            # if self.leader is None, then I'm the leader,
            # I always move!
            # print("LEADER BLOB MOVING TOWARDS PLAYER", self)
            before = self.pos
            self.move_towards_player()
            move = self.pos - before
            for b in self.blobs:
                if b is self:
                    continue
                dist = 1 / (0.3 + (self.pos - b.pos).magnitude / 300)
                b.pos += move * dist

            return

        # only move towards the leader if I'm not
        # touching any other blobs
        self.move_towards_pos(
            self.leader.pos * 0.9 +
            self.level.player.pos * 0.1
        )


def Blob(level, count=30):
    leader = Bloblet(level, None)
    for i in range(count-1):
        level.enemies.append(Bloblet(level, leader))
    return leader


class Shot(BadGuy):
    radius = 2
    speed = 4
    lifetime = 2
    die_on_any_collision = True

    def __init__(self, shooter):
        super().__init__(shooter.level)
        player = self.level.player
        self.shooter = shooter
        self.pos = Vector2D(shooter.shape.pos[0], shooter.shape.pos[1])
        self.delta = (player.pos - self.pos).scaled(self.speed)
        self.shape = MagicMissile(self.level, self.pos, self.delta)
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

    def delete(self):
        super().delete()
        self.shape.hit()


class ShooterBase(BadGuy):
    min_time = 0.5
    max_time = 1.5

    speed = 0.3
    radius = 8

    def _next_shot_time(self):
        self.next_shot_time = self.level.game.time + self.min_time + (random.random() * (self.max_time - self.min_time))

    def make_shot(self):
        raise RuntimeError("virtual make_shot fn called")

    def shoot(self):
        shot = self.make_shot()
        if shot:
            self.level.enemies.append(shot)
        self._next_shot_time()

    def move(self):
        raise RuntimeError("virtual move fn called")

    def update(self, dt):
        if self.dead:
            return
        self.move(dt)
        if self.level.game.time >= self.next_shot_time:
            self.shoot()


class Shooter(ShooterBase):
    final_speed = ShooterBase.speed

    def __init__(self, level, pos=None, speed_boost=None, period=None):
        super().__init__(level)
        self.shape = level.scene.layers[Layers.ENTITIES].add_sprite(
            'skeleton-head',
            color=(0.7, 0.6, 0.6, 1),
        )
        self.shape.scale = 1.3
        if pos == None:
            self.random_placement()
        else:
            self.pos = self.shape.pos = pos
        self.init_spot()

        if speed_boost:
            self.initial_speed = self.speed = speed_boost
            self.start_time = self.level.game.time
            self.period = period
        else:
            self.initial_speed = None
            self.speed = self.final_speed

        self.level.shooters.add(self)
        self._next_shot_time()
        clock.each_tick(self.smoke)

    SMOKE_RATE = 100

    def smoke(self, dt):
        self.level.scene.smoke.emit(
            num=dt * self.SMOKE_RATE,
            pos=Vector2D(self.shape.pos) - Polar2D(5, self.shape.angle),
            vel_spread=30,
            spin_spread=1,
            size=8,
            size_spread=3,
            angle_spread=3,
            color='#000000ff'
        )

    def delete(self):
        self.level.shooters.discard(self)
        clock.unschedule(self.smoke)
        self.level.scene.skulls.emit(
            1,
            pos=self.pos,
            vel_spread=80,
            spin_spread=1,
            size=8,
        )
        super().delete()

    def make_shot(self):
        return Shot(self)

    def move(self, dt):
        if self.initial_speed:
            elapsed = self.level.game.time - self.start_time
            if elapsed >= self.period:
                self.speed = self.final_speed
                self.initial_speed = None
            else:
                ratio = (self.period - elapsed) / self.period
                current_speed = self.final_speed + ((self.initial_speed - self.final_speed) * ratio)
                self.speed = current_speed
        player = self.level.player
        self.shape.angle = Vector2D(player.pos - self.shape.pos).angle()
        self.move_towards_spot()


class Spawner(ShooterBase):

    min_time = 0.6
    max_time = 1.4

    spawn_distance = 20
    radius = 20

    def __init__(self, level, corner):
        super().__init__(level)
        scene = level.scene
        self.shape = scene.layers[Layers.UPPER_ENTITIES].add_sprite('spawner')

        # start some distance away from our corner
        screen_center = Vector2D(scene.width / 2, scene.height / 2)
        delta = screen_center - corner

        self.final_position = corner + delta.scaled(math.sqrt(self.radius) * 1.1)

        delta = delta.scaled(delta.magnitude * (0.4 + (random.random() * 0.3)))
        one_sixth_tau = math.tau / 6
        one_twelfth_tau = math.tau / 12
        delta = delta.rotated(one_twelfth_tau - (random.random() * one_sixth_tau))
        self.pos = self.shape.pos = corner + delta

        self._next_shot_time()
        self.t = random.uniform(0, 6)
        clock.each_tick(self.bob)

    def bob(self, dt):
        self.t += dt
        self.shape.scale = 1 + 0.1 * np.sin(self.t * 4)
        delta = self.level.player.pos - self.pos
        self.shape.angle = delta.angle()

    def delete(self):
        clock.unschedule(self.bob)
        super().delete()

    def make_shot(self):
        if len(self.level.shooters) >= 10:
            return None

        delta = self.level.player.pos - self.pos
        if delta.magnitude > self.spawn_distance:
            delta = delta.scaled(self.spawn_distance)
        shooter = Shooter(self.level, pos=self.pos + delta, speed_boost=8.0, period=0.2)
        return shooter

    def move(self, dt):
        self.move_towards_pos(self.final_position)


class Prince(Entity):
    radius = 20

    def __init__(self, level, pos):
        super().__init__(level)
        self.layer = level.scene.layers[Layers.ENTITIES]
        self.shape = self.layer.add_sprite('prince')
        self.pos = self.shape.pos = pos
        self.hearts = level.scene.layers[Layers.HUD].add_particle_group(
            texture='heart',
            grow=1.1,
            max_age=3,
            gravity=(0, -100),
            drag=0.1,
        )
        self.hearts.add_color_stop(0, (1, 1, 1, 0))
        self.hearts.add_color_stop(0.2, (1, 1, 1, 1))
        self.hearts.add_color_stop(1, (1, 1, 1, 1))
        self.hearts.add_color_stop(3, (1, 1, 1, 0))
        self.level.objects.append(self)

    def on_collide_player(self):
        self.level.game.win()

    def on_collide_zone(self):
        self.die()

    def delete(self):
        self.level.objects.remove(self)
        if self.shape:
            self.shape.delete()
            self.hearts.delete()
            self.shape = None

    def die(self, v):
        self.level.game.lose("You killed the prince!")
        self.delete()

    def move_delta(self, d):
        pass

    HEART_RATE = 1

    def update(self, dt):
        if not self.shape:
            return
        self.shape.angle = (self.level.player.pos - self.pos).angle()
        self.hearts.emit(
            num=np.random.poisson(dt * self.HEART_RATE),
            pos=Vector2D(self.shape.pos) - Vector2D(0, 30),
            vel_spread=30,
            size=5,
            size_spread=2,
        )
