from wasabi2d import Scene, event, animate, sounds
from pathlib import Path
import sys

import ascend

from . import control
from .constants import Layers
from .level import Level
from .vector2d import Vector2D, Polar2D


__all__ = [
    'Game',
]


class Game:
    def __init__(self, settings, gametype):
        self.settings = settings
        self.gametype = gametype

        self.scene = None
        self.level = None
        self.time = 0.0
        self.frame = 0
        self.paused = False

        if len(sys.argv) > 1:
            self.new_game_level = sys.argv[1]
        else:
            self.new_game_level = "title screen"

        self.reset_game()

        event(self.update)
        self.create_scene()

    def create_scene(self):
        print("[INFO] Creating scene...")
        self.scene = scene = Scene(
            1024,
            768,
            title="Ascend",
            rootdir=Path(ascend.__file__).parent
        )

        scene.background = (0.2, 0.2, 0.2)

    def init_scene(self):
        scene = self.scene

        scene.layers[Layers.LOWER_EFFECTS].set_effect(
            'dropshadow',
            radius=2,
            offset=(1.5, 1.5)
        )
        scene.layers[Layers.ENTITIES].set_effect(
            'dropshadow',
            radius=3,
            offset=(3, 3)
        )
        scene.layers[Layers.TEXT].set_effect(
            'dropshadow',
            radius=3,
            offset=(3, 3)
        )
        scene.layers[Layers.UPPER_EFFECTS].set_effect(
            'bloom',
            radius=10,
        )

        smoke = scene.layers[Layers.LOWER_EFFECTS].add_particle_group(
            texture='smoke',
            grow=0.1,
            max_age=0.8,
            drag=0.1,
        )
        smoke.add_color_stop(0, '#888888ff')
        smoke.add_color_stop(0.6, '#888888ff')
        smoke.add_color_stop(0.8, '#88888800')
        scene.smoke = smoke

        sparks = scene.layers[Layers.UPPER_EFFECTS].add_particle_group(
            texture='spark',
            grow=0.1,
            max_age=0.6,
            drag=0.7,
        )
        sparks.add_color_stop(0, (2, 2, 0.8, 1))
        sparks.add_color_stop(0.3, (2, 1, 0, 1))
        sparks.add_color_stop(0.6, (0, 0, 0, 0))
        scene.sparks = sparks

        scene.bones = scene.layers[Layers.DEBRIS].add_particle_group(
            texture='bone',
            max_age=4,
            drag=0.1,
            spin_drag=0.4,
        )
        scene.skulls = scene.layers[Layers.DEBRIS].add_particle_group(
            texture='skull',
            max_age=4,
            drag=0.1,
            spin_drag=0.4,
        )
        for pgroup in (scene.bones, scene.skulls):
            pgroup.add_color_stop(0, '#bbbbbbff')
            pgroup.add_color_stop(1, '#bbbbbbff')
            pgroup.add_color_stop(4, '#bbbbbb00')

    def clear_scene(self):
        for layer in dir(Layers):
            if layer.startswith("_"):
                continue
            value = getattr(Layers, layer)
            self.scene.layers[value].clear()

    def new(self):
        print("[INFO] New game.")
        level = Level(self, self.new_game_level)
        return self.go_to_level(level)

    def reset_game(self):
        self.lives = 4

    def go_to_level(self, level):
        print(f"[INFO] Switch to level {level}.")

        self.delete()

        self.paused = False

        self.init_scene()

        self.level = level
        level.populate()

    def delete(self):
        self.clear_scene()
        self.delete_level()

    def delete_level(self):
        if self.level:
            self.level.delete()
            self.level = None

    def update(self, t, dt, keyboard):
        self.time += dt
        self.frame += 1

        if keyboard.escape:
            sys.exit("[INFO] Quittin' time!")

        if self.level:
            self.level.update(t, dt, keyboard)


    def win(self):
        self.paused = True
        self.level.win()

    def lose(self, text):
        self.paused = True
        self.level.lose(text)
