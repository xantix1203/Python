"""Client-side input guards in MatchView: which cells a player may fire at, and
panel selection. Uses SDL's dummy video driver so no real window is needed.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame as pg
import pytest

from battleship.config import BOARD_SIZE, CELL_SIZE, COLOR_WHITE, SPECIAL_COSTS, USA_MAX_CASTS
from battleship.models.grid import Grid
from battleship.ui import board_view
from battleship.ui.match_view import _BANNER_COLORS, _PAKISTAN_ACCEPT_RECT, _PAKISTAN_REFUSE_RECT, MatchView


@pytest.fixture
def view():
    pg.init()
    pg.display.set_mode((10, 10))
    # Congo: a real country with no interactive-picking special (unlike USA/
    # Italy), so the generic Phase 1 cast tests below stay about the generic
    # pathway, not a targeted one.
    seats = [{"name": "Me", "country": "Congo"}, {"name": "Foe", "country": "China"}, {"name": "Gone", "country": "Russia"}]
    view = MatchView(pg.display.get_surface(), conn=None, me=0, seats=seats, my_grid=Grid())
    view.state = {
        "turn": 0,
        "extra": False,
        "over": False,
        "winner": None,
        "sinks": [],
        "boards": [
            {"owner": "Me", "country": "Congo", "score": 0, "energy": 0, "shielded": False, "congo_cooldown": False, "usa_casts": 0,
             "alive": True, "ships_left": 5, "shots": [], "sunk": []},
            {"owner": "Foe", "country": "China", "score": 0, "energy": 0, "shielded": False, "congo_cooldown": False, "usa_casts": 0,
             "alive": True, "ships_left": 5, "shots": [[4, 4, True]], "sunk": []},
            {"owner": "Gone", "country": "Russia", "score": 0, "energy": 0, "shielded": False, "congo_cooldown": False, "usa_casts": 0,
             "alive": False, "ships_left": 0, "shots": [], "sunk": []},
        ],
    }
    return view


def _make_targeted_view(country, energy=0):
    seats = [{"name": "Me", "country": country}, {"name": "Foe", "country": "China"}]
    view = MatchView(pg.display.get_surface(), conn=None, me=0, seats=seats, my_grid=Grid())
    view.state = {
        "turn": 0,
        "extra": False,
        "over": False,
        "winner": None,
        "sinks": [],
        "boards": [
            {"owner": "Me", "country": country, "score": 0, "energy": energy, "shielded": False,
             "congo_cooldown": False, "usa_casts": 0, "alive": True, "ships_left": 5, "shots": [], "sunk": []},
            {"owner": "Foe", "country": "China", "score": 0, "energy": 0, "shielded": False, "congo_cooldown": False, "usa_casts": 0,
             "alive": True, "ships_left": 5, "shots": [], "sunk": []},
        ],
    }
    view.selected = 1
    return view


def _stub_conn(view):
    sent = []
    view.conn = type("C", (), {"send": lambda self, msg: sent.append(msg)})()
    return sent


def _pixel(cell):
    """A canvas-space pixel position landing inside `cell`, the coordinate
    space _submit_targeted_cast expects (it converts back via cell_from_pos,
    the same as a real mouse click would)."""
    x, y = cell
    return (x * CELL_SIZE + 5, y * CELL_SIZE + 5)


def test_can_fire_at_an_unshot_cell_of_a_living_opponent_on_my_turn(view):
    view.selected = 1
    assert view._can_fire((2, 3)) is True


def test_cannot_fire_at_a_shielded_opponent(view):
    view.selected = 1
    view.state["boards"][1]["shielded"] = True
    assert view._can_fire((2, 3)) is False


def test_cannot_fire_at_an_already_shot_cell(view):
    view.selected = 1
    assert view._can_fire((4, 4)) is False


def test_cannot_fire_at_your_own_board(view):
    view.selected = 0
    assert view._can_fire((2, 3)) is False


def test_cannot_fire_at_an_eliminated_player(view):
    view.selected = 2
    assert view._can_fire((2, 3)) is False


def test_cannot_fire_when_it_is_not_your_turn(view):
    view.state["turn"] = 1
    view.selected = 1
    assert view._can_fire((2, 3)) is False


def test_clicking_a_panel_tile_selects_that_board(view):
    seat, rect = view._tile_rects()[1]
    view._select_from_panel(rect.center)
    assert view.selected == 1


def test_apply_event_shows_the_latest_event_as_a_banner(view):
    view._apply_event({"text": "line 1", "kind": "miss", "shooter": 0, "target": 1, "cell": None, "hit": False})
    view._apply_event({"text": "line 2", "kind": "hit", "shooter": 0, "target": 1, "cell": None, "hit": True})
    text, color, expires_at, boat_name = view._banner
    assert text == "line 2"
    assert color == _BANNER_COLORS["hit"]
    assert expires_at > pg.time.get_ticks()
    assert boat_name is None


def test_apply_event_gives_a_cast_banner_more_screen_time(view):
    view._apply_event({"text": "hit", "kind": "hit", "shooter": 0, "target": 1, "cell": None, "hit": True})
    _, _, hit_expiry, _ = view._banner

    view._apply_event({"text": "cast", "kind": "cast", "shooter": 0, "target": None, "cell": None, "hit": False})
    _, _, cast_expiry, _ = view._banner

    assert cast_expiry - pg.time.get_ticks() > hit_expiry - pg.time.get_ticks()


def test_apply_event_carries_the_boat_name_for_a_banner():
    view = _make_targeted_view("China")
    view._apply_event(
        {"text": "P0 a touché le torpilleur de P1.", "kind": "hit", "shooter": 0, "target": 1, "cell": [0, 0],
         "hit": True, "boat_name": "torpilleur"}
    )

    _, _, _, boat_name = view._banner

    assert boat_name == "torpilleur"


def test_banner_segments_highlights_the_boat_name(view):
    segments = view._banner_segments("P0 a coulé le Titanic de P1 !", COLOR_WHITE, "Titanic")

    assert segments == [("P0 a coulé le ", COLOR_WHITE), ("Titanic", (255, 215, 0)), (" de P1 !", COLOR_WHITE)]


def test_banner_segments_is_a_single_segment_without_a_boat_name(view):
    segments = view._banner_segments("P0 a raté P1.", COLOR_WHITE, None)

    assert segments == [("P0 a raté P1.", COLOR_WHITE)]


def test_banner_expires_after_its_duration(view, monkeypatch):
    view._apply_event({"text": "line 1", "kind": "miss", "shooter": 0, "target": 1, "cell": None, "hit": False})
    monkeypatch.setattr(pg.time, "get_ticks", lambda: view._banner[2] + 1)
    view._draw_banner()
    assert view._banner is None


def test_banner_colors_include_a_cast_entry():
    assert "cast" in _BANNER_COLORS


def test_can_cast_when_energy_covers_the_cost(view):
    view.state["boards"][0]["energy"] = view._special_cost
    assert view._can_cast() is True


def test_cannot_cast_when_energy_is_short(view):
    view.state["boards"][0]["energy"] = view._special_cost - 1
    assert view._can_cast() is False


def test_cannot_cast_when_it_is_not_your_turn(view):
    view.state["turn"] = 1
    view.state["boards"][0]["energy"] = view._special_cost
    assert view._can_cast() is False


def test_try_cast_sends_a_cast_message_when_affordable(view):
    view.state["boards"][0]["energy"] = view._special_cost
    sent = []
    view.conn = type("C", (), {"send": lambda self, msg: sent.append(msg)})()

    view._try_cast()

    assert sent == [{"type": "cast", "payload": {}}]


def test_try_cast_sends_nothing_when_not_affordable(view):
    view.state["boards"][0]["energy"] = 0
    sent = []
    view.conn = type("C", (), {"send": lambda self, msg: sent.append(msg)})()

    view._try_cast()

    assert sent == []


# --- targeted specials (USA/Italy): picking-mode state machine -------------


def test_try_cast_enters_picking_mode_for_a_targeted_special():
    view = _make_targeted_view("USA", energy=SPECIAL_COSTS["USA"])
    sent = _stub_conn(view)

    view._try_cast()

    assert view._picking is True
    assert sent == []  # nothing sent yet -- waiting for the target/geometry pick


def test_escape_cancels_picking():
    view = _make_targeted_view("USA", energy=SPECIAL_COSTS["USA"])
    view._picking = True

    view._handle_key(type("FakeKeyEvent", (), {"key": pg.K_ESCAPE})())

    assert view._picking is False


def test_r_toggles_axis_for_italy_only():
    view = _make_targeted_view("Italy", energy=SPECIAL_COSTS["Italy"])
    view._picking = True
    assert view._pick_axis == "row"

    view._handle_key(type("FakeKeyEvent", (), {"key": pg.K_r})())
    assert view._pick_axis == "col"

    view._handle_key(type("FakeKeyEvent", (), {"key": pg.K_r})())
    assert view._pick_axis == "row"


def test_submit_targeted_cast_sends_usa_payload():
    view = _make_targeted_view("USA", energy=SPECIAL_COSTS["USA"])
    view._picking = True
    sent = _stub_conn(view)

    view._submit_targeted_cast(_pixel((2, 3)))

    assert sent == [{"type": "cast", "payload": {"target": 1, "x": 2, "y": 3}}]
    assert view._picking is False


def test_submit_targeted_cast_rejects_a_usa_block_that_would_go_out_of_bounds():
    view = _make_targeted_view("USA", energy=SPECIAL_COSTS["USA"])
    view._picking = True
    sent = _stub_conn(view)

    view._submit_targeted_cast(_pixel((BOARD_SIZE - 1, 0)))

    assert sent == []
    assert view._picking is False  # picking still ends -- same silent-drop as any illegal action


def test_submit_targeted_cast_sends_italy_payload_for_the_current_axis():
    view = _make_targeted_view("Italy", energy=SPECIAL_COSTS["Italy"])
    view._picking = True
    view._pick_axis = "col"
    sent = _stub_conn(view)

    view._submit_targeted_cast(_pixel((2, 3)))

    assert sent == [{"type": "cast", "payload": {"target": 1, "axis": "col", "index": 2}}]


def test_submit_targeted_cast_rejects_targeting_your_own_board():
    view = _make_targeted_view("USA", energy=SPECIAL_COSTS["USA"])
    view.selected = view.me
    view._picking = True
    sent = _stub_conn(view)

    view._submit_targeted_cast(_pixel((2, 3)))

    assert sent == []


def test_targeted_cells_previews_the_usa_block():
    view = _make_targeted_view("USA", energy=SPECIAL_COSTS["USA"])
    view._cursor_cell = (2, 3)

    cells = view._targeted_cells()

    assert len(cells) == 16
    assert set(cells) == {(2 + dx, 3 + dy) for dx in range(4) for dy in range(4)}


def test_targeted_cells_is_none_for_a_usa_block_that_would_not_fit():
    view = _make_targeted_view("USA", energy=SPECIAL_COSTS["USA"])
    view._cursor_cell = (BOARD_SIZE - 1, 0)

    assert view._targeted_cells() is None


def test_targeted_cells_previews_the_italy_row_or_column():
    view = _make_targeted_view("Italy", energy=SPECIAL_COSTS["Italy"])
    view._cursor_cell = (4, 6)

    view._pick_axis = "row"
    assert set(view._targeted_cells()) == {(x, 6) for x in range(BOARD_SIZE)}

    view._pick_axis = "col"
    assert set(view._targeted_cells()) == {(4, y) for y in range(BOARD_SIZE)}


def test_try_cast_sends_target_immediately_for_an_opponent_target_special():
    view = _make_targeted_view("Bresil", energy=SPECIAL_COSTS["Bresil"])
    sent = _stub_conn(view)

    view._try_cast()

    assert sent == [{"type": "cast", "payload": {"target": 1}}]
    assert view._picking is False  # no picking mode needed -- sent immediately


def test_try_cast_sends_nothing_for_an_opponent_target_special_on_your_own_board():
    view = _make_targeted_view("Bresil", energy=SPECIAL_COSTS["Bresil"])
    view.selected = view.me
    sent = _stub_conn(view)

    view._try_cast()

    assert sent == []


def test_apply_bresil_theft_adds_the_boat_to_the_thiefs_own_grid():
    view = _make_targeted_view("Bresil")

    view._apply_event(
        {
            "text": "t",
            "kind": "cast",
            "shooter": 0,
            "target": 1,
            "cell": None,
            "hit": False,
            "special": "Bresil",
            "boat_name": "Stolen",
            "stolen_cells": [[0, 1], [1, 1]],
            "new_cells": [[5, 5], [5, 6]],
            "eliminated": True,
        }
    )

    boat = next(b for b in view.my_grid.floating_boats if (5, 5) in [c for c, _ in b.cells])
    assert boat.name == "Stolen"
    assert {c for c, _ in boat.cells} == {(5, 5), (5, 6)}


def test_apply_bresil_theft_removes_the_boat_from_the_victims_own_grid():
    view = _make_targeted_view("China")  # any non-thief seat: view.me == 0, but here we play the victim (seat 1)
    view.me = 1
    boat = view.my_grid.add_boat([(0, 1), (1, 1)], name="Mine")

    view._apply_event(
        {
            "text": "t",
            "kind": "cast",
            "shooter": 0,
            "target": 1,
            "cell": None,
            "hit": False,
            "special": "Bresil",
            "boat_name": "Mine",
            "stolen_cells": [[0, 1], [1, 1]],
            "new_cells": [[5, 5], [5, 6]],
            "eliminated": True,
        }
    )

    assert boat not in view.my_grid.floating_boats


def test_apply_event_revives_my_own_boat_from_revived_cells():
    view = _make_targeted_view("URSS")
    boat = view.my_grid.add_boat([(0, 0), (1, 0)])
    view.my_grid.floating_boats.remove(boat)
    view.my_grid.sunk_boats.append(boat)
    for cell_entry in boat.cells:
        cell_entry[1] = True
    boat.hits_remaining = 0

    view._apply_event(
        {
            "text": "t",
            "kind": "cast",
            "shooter": 0,
            "target": None,
            "cell": None,
            "hit": False,
            "special": "URSS",
            "revived_cells": [[0, 0], [1, 0]],
        }
    )

    assert boat in view.my_grid.floating_boats
    assert boat not in view.my_grid.sunk_boats
    assert boat.hits_remaining == boat.size


# --- Congo: shielded opponents disappear from the ribbon --------------------


def test_shielded_opponent_tile_is_hidden_from_others(view):
    view.state["boards"][1]["shielded"] = True
    assert view._tile_visible(1) is False


def test_shielded_own_tile_stays_visible_to_yourself(view):
    view.state["boards"][0]["shielded"] = True
    assert view._tile_visible(0) is True


def test_select_from_panel_ignores_a_hidden_shielded_tile(view):
    view.state["boards"][1]["shielded"] = True
    seat, rect = view._tile_rects()[1]

    view._select_from_panel(rect.center)

    assert view.selected == view.me  # unchanged -- the hidden tile can't be clicked


def test_first_opponent_skips_a_shielded_player_when_another_is_available():
    seats = [{"name": "Me", "country": "China"}, {"name": "A", "country": "USA"}, {"name": "B", "country": "Italy"}]
    view = MatchView(pg.display.get_surface(), conn=None, me=0, seats=seats, my_grid=Grid())
    view.state = {
        "turn": 0, "extra": False, "over": False, "winner": None, "sinks": [],
        "boards": [
            {"owner": "Me", "country": "China", "score": 0, "energy": 0, "shielded": False,
             "congo_cooldown": False, "usa_casts": 0, "alive": True, "ships_left": 5, "shots": [], "sunk": []},
            {"owner": "A", "country": "USA", "score": 0, "energy": 0, "shielded": True,
             "congo_cooldown": False, "usa_casts": 0, "alive": True, "ships_left": 5, "shots": [], "sunk": []},
            {"owner": "B", "country": "Italy", "score": 0, "energy": 0, "shielded": False,
             "congo_cooldown": False, "usa_casts": 0, "alive": True, "ships_left": 5, "shots": [], "sunk": []},
        ],
    }

    assert view._first_opponent() == 2  # skips the shielded seat 1


def test_apply_state_moves_the_view_off_a_board_that_just_got_shielded():
    # 3 living opponents so there's actually somewhere better to switch to --
    # with only one, the fallback in _first_opponent has no choice but to
    # stay on it (see test_first_opponent's fallback-to-any-alive case).
    seats = [{"name": "Me", "country": "China"}, {"name": "A", "country": "USA"}, {"name": "B", "country": "Italy"}]
    view = MatchView(pg.display.get_surface(), conn=None, me=0, seats=seats, my_grid=Grid())
    view.state = {
        "turn": 0, "extra": False, "over": False, "winner": None, "sinks": [],
        "boards": [
            {"owner": "Me", "country": "China", "score": 0, "energy": 0, "shielded": False,
             "congo_cooldown": False, "usa_casts": 0, "alive": True, "ships_left": 5, "shots": [], "sunk": []},
            {"owner": "A", "country": "USA", "score": 0, "energy": 0, "shielded": False,
             "congo_cooldown": False, "usa_casts": 0, "alive": True, "ships_left": 5, "shots": [], "sunk": []},
            {"owner": "B", "country": "Italy", "score": 0, "energy": 0, "shielded": False,
             "congo_cooldown": False, "usa_casts": 0, "alive": True, "ships_left": 5, "shots": [], "sunk": []},
        ],
    }
    view.selected = 1

    new_state = dict(view.state)
    new_state["boards"] = [dict(b) for b in view.state["boards"]]
    new_state["boards"][1]["shielded"] = True

    view._apply_state(new_state)

    assert view.selected == 2  # moved off the now-shielded seat 1 onto seat 2


def test_congo_cooldown_hint_is_drawn_next_to_the_button(view):
    view.state["boards"][0]["congo_cooldown"] = True
    # Just confirm this renders without error with the hint active.
    view.render()


def test_cannot_cast_once_usa_has_used_both_casts():
    view = _make_targeted_view("USA", energy=SPECIAL_COSTS["USA"])
    view.state["boards"][0]["usa_casts"] = USA_MAX_CASTS

    assert view._can_cast() is False


def test_can_still_cast_usa_below_the_cap():
    view = _make_targeted_view("USA", energy=SPECIAL_COSTS["USA"])
    view.state["boards"][0]["usa_casts"] = USA_MAX_CASTS - 1

    assert view._can_cast() is True


def test_cast_hint_explains_the_usa_cap_once_reached():
    view = _make_targeted_view("USA", energy=SPECIAL_COSTS["USA"])
    view.state["boards"][0]["usa_casts"] = USA_MAX_CASTS

    assert view._cast_hint_text() == f"déjà utilisé {USA_MAX_CASTS}/{USA_MAX_CASTS} fois"


def test_cast_hint_is_none_for_usa_below_the_cap():
    view = _make_targeted_view("USA", energy=SPECIAL_COSTS["USA"])
    view.state["boards"][0]["usa_casts"] = USA_MAX_CASTS - 1

    assert view._cast_hint_text() is None


def test_usa_cap_hint_renders_without_error():
    usa_view = _make_targeted_view("USA", energy=SPECIAL_COSTS["USA"])
    usa_view.state["boards"][0]["usa_casts"] = USA_MAX_CASTS
    usa_view.render()


def test_cast_button_label_has_no_emoji_or_placeholder_text(view):
    assert "⚡" not in view._cast_button.label
    assert "NRJ" not in view._cast_button.label


def test_cast_button_draws_a_vector_energy_icon_instead_of_text(view, monkeypatch):
    calls = []
    monkeypatch.setattr(board_view, "draw_energy_icon", lambda *a, **k: calls.append((a, k)))

    view._draw_cast_button()

    assert len(calls) == 1


def test_shielded_own_tile_draws_a_vector_shield_icon_instead_of_text(view, monkeypatch):
    view.state["boards"][0]["shielded"] = True
    calls = []
    monkeypatch.setattr(board_view, "draw_shield_icon", lambda *a, **k: calls.append((a, k)))
    seat, rect = view._tile_rects()[0]

    view._draw_tile(0, rect)

    assert len(calls) == 1


def test_unshielded_tile_draws_no_shield_icon(view, monkeypatch):
    calls = []
    monkeypatch.setattr(board_view, "draw_shield_icon", lambda *a, **k: calls.append((a, k)))
    seat, rect = view._tile_rects()[0]

    view._draw_tile(0, rect)

    assert calls == []


# --- China: counterfeit (self) vs. surveillance (opponent, picking) --------


def test_try_cast_sends_counterfeit_payload_when_viewing_your_own_board():
    view = _make_targeted_view("China", energy=SPECIAL_COSTS["China"])
    view.selected = view.me
    sent = _stub_conn(view)

    view._try_cast()

    assert sent == [{"type": "cast", "payload": {"mode": "counterfeit"}}]
    assert view._picking is False


def test_try_cast_enters_picking_mode_for_surveillance_when_viewing_an_opponent():
    view = _make_targeted_view("China", energy=SPECIAL_COSTS["China"])  # selected defaults to opponent seat 1
    sent = _stub_conn(view)

    view._try_cast()

    assert view._picking is True
    assert sent == []


def test_r_toggles_axis_for_china_too():
    view = _make_targeted_view("China", energy=SPECIAL_COSTS["China"])
    view._picking = True
    assert view._pick_axis == "row"

    view._handle_key(type("FakeKeyEvent", (), {"key": pg.K_r})())
    assert view._pick_axis == "col"


def test_submit_targeted_cast_sends_china_surveillance_payload_for_the_low_half():
    view = _make_targeted_view("China", energy=SPECIAL_COSTS["China"])
    view._picking = True
    view._pick_axis = "row"
    sent = _stub_conn(view)

    view._submit_targeted_cast(_pixel((2, 3)))  # row 3 -> low half (rows 0-4)

    assert sent == [{"type": "cast", "payload": {"target": 1, "mode": "surveillance", "axis": "row", "half": "low"}}]
    assert view._picking is False


def test_submit_targeted_cast_sends_china_surveillance_payload_for_the_high_half():
    view = _make_targeted_view("China", energy=SPECIAL_COSTS["China"])
    view._picking = True
    view._pick_axis = "col"
    sent = _stub_conn(view)

    view._submit_targeted_cast(_pixel((7, 2)))  # col 7 -> high half (cols 5-9)

    assert sent == [{"type": "cast", "payload": {"target": 1, "mode": "surveillance", "axis": "col", "half": "high"}}]


def test_targeted_cells_previews_chinas_row_half():
    view = _make_targeted_view("China", energy=SPECIAL_COSTS["China"])
    view._pick_axis = "row"
    view._cursor_cell = (4, 2)  # row 2 -> low half

    assert set(view._targeted_cells()) == {(x, y) for y in range(5) for x in range(BOARD_SIZE)}


def test_targeted_cells_previews_chinas_column_half():
    view = _make_targeted_view("China", energy=SPECIAL_COSTS["China"])
    view._pick_axis = "col"
    view._cursor_cell = (7, 4)  # col 7 -> high half

    assert set(view._targeted_cells()) == {(x, y) for x in range(5, BOARD_SIZE) for y in range(BOARD_SIZE)}


def test_apply_reveal_stores_the_revealed_cells_with_an_expiry():
    view = _make_targeted_view("China")

    view._apply_reveal({"target": 1, "cells": [[2, 3], [2, 4]]})

    assert view._reveal["target"] == 1
    assert view._reveal["cells"] == [(2, 3), (2, 4)]
    assert view._reveal["expires_at"] > pg.time.get_ticks()


def test_draw_reveal_clears_itself_after_expiry(monkeypatch):
    view = _make_targeted_view("China")
    view._apply_reveal({"target": 1, "cells": [[2, 3]]})
    monkeypatch.setattr(pg.time, "get_ticks", lambda: view._reveal["expires_at"] + 1)

    view._draw_reveal(1)

    assert view._reveal is None


def test_draw_reveal_leaves_an_unrelated_board_alone():
    view = _make_targeted_view("China")
    view._apply_reveal({"target": 1, "cells": [[2, 3]]})

    view._draw_reveal(0)  # currently drawing a different board than the reveal's target

    assert view._reveal is not None  # untouched, just not drawn there


def test_apply_event_adds_a_fragile_decoy_to_my_grid_for_my_own_counterfeit():
    view = _make_targeted_view("China")

    view._apply_event(
        {
            "text": "t",
            "kind": "cast",
            "shooter": 0,
            "target": None,
            "cell": None,
            "hit": False,
            "special": "China",
            "mode": "counterfeit",
            "placed": True,
            "cells": [[5, 5], [5, 6]],
            "boat_name": "Contrefaçon (torpilleur)",
        }
    )

    boat = next(b for b in view.my_grid.floating_boats if (5, 5) in [c for c, _ in b.cells])
    assert boat.name == "Contrefaçon (torpilleur)"
    assert boat.hits_remaining == 1  # fragile, like Congo/URSS revivals


def test_apply_event_ignores_a_counterfeit_cast_by_someone_else():
    view = _make_targeted_view("China")

    view._apply_event(
        {
            "text": "t",
            "kind": "cast",
            "shooter": 1,
            "target": None,
            "cell": None,
            "hit": False,
            "special": "China",
            "mode": "counterfeit",
            "placed": True,
            "cells": [[5, 5], [5, 6]],
            "boat_name": "Decoy",
        }
    )

    assert view.my_grid.floating_boats == []


# --- Pakistan: Accept/Refuse prompt blocks input until answered -------------


def test_apply_prompt_sets_the_pakistan_prompt_with_an_expiry():
    view = _make_targeted_view("China")

    view._apply_prompt({"type": "prompt", "kind": "pakistan", "deadline_ms": 5000})

    assert view._pakistan_prompt is not None
    assert view._pakistan_prompt["expires_at"] > pg.time.get_ticks()


def test_apply_prompt_ignores_an_unknown_kind():
    view = _make_targeted_view("China")

    view._apply_prompt({"type": "prompt", "kind": "something_else", "deadline_ms": 5000})

    assert view._pakistan_prompt is None


def test_accepting_the_pakistan_prompt_sends_a_respond_message_and_clears_it():
    view = _make_targeted_view("China")
    view._pakistan_prompt = {"expires_at": pg.time.get_ticks() + 5000}
    sent = _stub_conn(view)

    view._handle_pakistan_click(_PAKISTAN_ACCEPT_RECT.center)

    assert sent == [{"type": "respond", "choice": "accept"}]
    assert view._pakistan_prompt is None


def test_refusing_the_pakistan_prompt_sends_a_respond_message_and_clears_it():
    view = _make_targeted_view("China")
    view._pakistan_prompt = {"expires_at": pg.time.get_ticks() + 5000}
    sent = _stub_conn(view)

    view._handle_pakistan_click(_PAKISTAN_REFUSE_RECT.center)

    assert sent == [{"type": "respond", "choice": "refuse"}]
    assert view._pakistan_prompt is None


def test_pakistan_prompt_swallows_a_click_that_hits_neither_button():
    view = _make_targeted_view("China", energy=SPECIAL_COSTS["China"])
    view._pakistan_prompt = {"expires_at": pg.time.get_ticks() + 5000}
    sent = _stub_conn(view)
    fake_event = type("FakeMouseEvent", (), {"type": pg.MOUSEBUTTONDOWN, "button": 1, "pos": _pixel((2, 3))})()

    view._handle_input(fake_event)

    assert sent == []  # the click landed on the board, not either prompt button -- swallowed, not fired


def test_draw_pakistan_prompt_clears_itself_after_expiry(monkeypatch):
    view = _make_targeted_view("China")
    view._pakistan_prompt = {"expires_at": pg.time.get_ticks() + 100}
    monkeypatch.setattr(pg.time, "get_ticks", lambda: view._pakistan_prompt["expires_at"] + 1)

    view._draw_pakistan_prompt()

    assert view._pakistan_prompt is None


def test_render_with_a_pending_pakistan_prompt(view):
    view._pakistan_prompt = {"expires_at": pg.time.get_ticks() + 5000}
    view.render()  # just confirm this renders without error while the modal is up
