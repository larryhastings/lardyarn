from wasabi2d import Scene, event, run, keys, Vector2
from ascend.triangle_intersect import polygon_collision
from pygame import joystick


scene = Scene()
scene.background = (0.2,) * 3
scene.layers[0].set_effect('dropshadow', radius=1)

triangle = [
    Vector2(100, 200),
    Vector2(300, 300),
    Vector2(200, 400)
]

scene.layers[0].add_polygon(triangle, fill=False, color='yellow')
circ = scene.layers[0].add_circle(radius=20, fill=False, color='red')


@event
def on_mouse_move(pos):
    circ.pos = pos
    pen = polygon_collision(triangle, pos, circ.radius)

    if pen:
        circ.pos -= pen
    circ.color = 'red' if pen else 'green'


run()
