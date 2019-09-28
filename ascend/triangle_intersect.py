#!/usr/bin/env python3
from .vector2d import Vector2D
import numpy as np


def normalize(vecs: np.ndarray) -> np.ndarray:
    xs = vecs[:, 0]
    ys = vecs[:, 1]
    mags = xs * xs + ys * ys
    return vecs / np.sqrt(mags)[:, np.newaxis]


def dot(xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
    return np.sum(xs * ys, axis=1, keepdims=True)


ROT90 = np.array([
    [0, 1],
    [-1, 0]
])


def polygon_collision(poly, circle_pos, circle_radius):
    points = np.array(poly)
    alongs = normalize(np.diff(points, axis=0, append=points[[0]]))
    across = alongs @ ROT90
    offs = dot(across, points)
    depths = dot(across, circle_pos) - offs + circle_radius
    if np.any(depths < 0):
        return None

    pen_edge = np.argmin(depths)
    pen = Vector2D(*across[pen_edge] * depths[pen_edge])

    relpts = points - circle_pos
    dists = np.hypot(relpts[:, 0], relpts[:, 1])

    closest = np.argmin(dists, axis=0)
    close_point = relpts[closest]

    if dists[closest] < 1e-5:
        return pen

    to_corner = close_point / np.linalg.norm(close_point)
    dists = dot(relpts, to_corner)
    if np.all(dists >= closest - 1e-5):
        if dists[closest] > circle_radius:
            return None
        else:
            return Vector2D(*to_corner * (circle_radius - dists[closest]))

    return pen
