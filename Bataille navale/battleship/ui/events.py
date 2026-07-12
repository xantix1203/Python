"""Small shared helpers for pygame event loops."""

import pygame as pg


def quit_if_closed(event):
    if event.type == pg.QUIT:
        pg.quit()
        raise SystemExit


def pump_and_wait(duration_ms):
    """Keep processing events (so closing the window still works) for a fixed pause."""
    deadline = pg.time.get_ticks() + duration_ms
    while pg.time.get_ticks() < deadline:
        for event in pg.event.get():
            quit_if_closed(event)
        pg.time.wait(16)
