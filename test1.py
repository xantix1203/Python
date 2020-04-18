import pygame as pg

pg.init()
blue_color = (90, 150, 255)
black_color = (0, 0, 0)
window = pg.display.set_mode((1000, 1000), pg.RESIZABLE)
window.fill(blue_color)
for i in range(1, 10):
    pg.draw.line(window, black_color, (100 * i, 0), (100 * i, 1000))
    pg.draw.line(window, black_color, (0, 100 * i), (1000, 100 * i))

pg.display.flip()
launched = True
while launched:
    for event in pg.event.get():
        if event.type == pg.QUIT:
            launched = False
