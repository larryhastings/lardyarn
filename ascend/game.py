from wasabi2d import Scene, event, run, clock
import pygame
from pathlib import Path
import sys

import ascend

from . import control
from .constants import Layers
from .level import Level


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

        scene.layers[Layers.WALL].set_effect(
            'dropshadow',
            radius=2,
            offset=(1.5, 1.5)
        )
        scene.layers[Layers.WALL].set_effect(
            'dropshadow',
            radius=3,
            offset=(3, 3)
        )
        scene.layers[Layers.LOWER_EFFECTS].set_effect(
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

        self.delete_level()
        self.paused = False

        self.init_scene()

        self.level = Level(self, self.gametype)

        return self.level

    def delete(self):
        self.delete_level()
        self.clear_scene()

    def delete_level(self):
        if self.level:
            self.level.delete()
            self.level = None

    def update(self, t, dt, keyboard):
        self.time += dt
        self.frame += 1

        if keyboard.escape:
            sys.exit("[INFO] Quittin' time!")

        if self.paused:
            if control.stick:
                for button in (0, 1, 2, 3):
                    if control.stick.get_button(button):
                        self.new()
                        break
            return

        if self.level:
            if not hasattr(self.level, "update"):
                print("LEVEL", self.level, type(self.level))
                print("DIR LEVEL", dir(self.level))
            self.level.update(t, dt, keyboard)
