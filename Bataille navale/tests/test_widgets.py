"""TextBox focus/placeholder/cursor behavior. Uses SDL's dummy video driver
so no real window is needed.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame as pg
import pytest

from battleship.ui.widgets import TextBox


@pytest.fixture(autouse=True)
def _init_pygame():
    pg.init()
    pg.display.set_mode((10, 10))


def _click(box, pos):
    box.handle_event(type("FakeMouseEvent", (), {"type": pg.MOUSEBUTTONDOWN, "button": 1, "pos": pos})())


def _key(box, key, unicode=""):
    box.handle_event(type("FakeKeyEvent", (), {"type": pg.KEYDOWN, "key": key, "unicode": unicode})())


def test_clicking_the_box_clears_the_placeholder_immediately():
    box = TextBox((0, 0, 220, 40), "Joueur 1")

    _click(box, (10, 10))

    assert box.text == ""
    assert box.active is True


def test_clicking_outside_the_box_does_not_clear_or_activate_it():
    box = TextBox((0, 0, 220, 40), "Joueur 1")

    _click(box, (500, 500))

    assert box.text == "Joueur 1"
    assert box.active is False


def test_typing_after_the_clearing_click_appends_normally():
    box = TextBox((0, 0, 220, 40), "Joueur 1")
    _click(box, (10, 10))

    _key(box, pg.K_a, "A")
    _key(box, pg.K_b, "B")

    assert box.text == "AB"


def test_reclicking_an_already_edited_box_does_not_wipe_typed_text():
    box = TextBox((0, 0, 220, 40), "Joueur 1")
    _click(box, (10, 10))
    _key(box, pg.K_a, "A")

    _click(box, (10, 10))  # click it again

    assert box.text == "A"


def test_a_locked_box_ignores_clicks():
    box = TextBox((0, 0, 220, 40), "Joueur 1")
    box.locked = True

    _click(box, (10, 10))

    assert box.text == "Joueur 1"
    assert box.active is False


def test_default_max_length_is_sixteen_characters():
    box = TextBox((0, 0, 220, 40), "")
    box.active = True
    box._edited = True  # skip the placeholder-clear-on-first-input step

    for letter in "abcdefghijklmnopqrstuvwxyz":  # far more than the cap
        _key(box, pg.K_a, letter)

    assert box.text == "abcdefghijklmnop"  # stopped at 16


def test_max_length_is_configurable_per_box():
    box = TextBox((0, 0, 440, 40), "", max_length=30)
    box.active = True
    box._edited = True

    for letter in "abcdefghijklmnopqrstuvwxyz0123456789":
        _key(box, pg.K_a, letter)

    assert box.text == "abcdefghijklmnopqrstuvwxyz0123"  # stopped at 30


def test_draw_shows_a_cursor_only_while_active_and_blinking_on(monkeypatch):
    box = TextBox((0, 0, 220, 40), "")
    window = pg.display.get_surface()
    font = pg.font.Font(None, 20)

    monkeypatch.setattr(pg.time, "get_ticks", lambda: 0)  # blink phase "on"
    calls = []
    monkeypatch.setattr(pg.draw, "line", lambda *a, **k: calls.append((a, k)))

    box.draw(window, font)  # inactive -- no cursor
    assert calls == []

    box.active = True
    box.draw(window, font)  # active, phase "on" -- cursor drawn
    assert len(calls) == 1

    monkeypatch.setattr(pg.time, "get_ticks", lambda: 500)  # blink phase "off"
    box.draw(window, font)
    assert len(calls) == 1  # unchanged -- no new draw this phase
