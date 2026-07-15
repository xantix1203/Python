"""Rendering and input for one player's view of an N-player free-targeting
match. Purely a view: it renders the authoritative `state` snapshots the server
broadcasts and turns clicks into `fire` intents -- it never resolves a shot
itself.

Layout: the full-size board of the currently-selected player fills the top
(reusing board_view's primitives at the window origin), and a bottom panel
holds the turn indicator and a clickable thumbnail per player (board + score
+ ships left + how many of YOUR ships they've sunk). Shot outcomes ("X hit
Y") are announced as a temporary banner over the middle of the board rather
than a persistent log, since they're transient news, not a reference list.
"""

import pygame as pg

from ..config import (
    BOARD_SIZE,
    COLOR_BLACK,
    COLOR_BLUE,
    COLOR_DARK_GREY,
    COLOR_GREY,
    COLOR_RED,
    COLOR_WHITE,
    MATCH_WINDOW_HEIGHT,
    SPECIAL_COSTS,
    USA_MAX_CASTS,
    WINDOW_SIZE,
)
from ..models.boat import Boat
from . import board_view, sound
from .events import play_flyover_animation, play_impact_animation, quit_if_closed
from .widgets import Button

_SEA = COLOR_BLUE
_HIGHLIGHT = (255, 215, 0)
_PANEL_TOP = WINDOW_SIZE
_TILE_TOP = _PANEL_TOP + 34
_MINI = 76  # px, side of a thumbnail board
_CAPTION_STEP = 17
_CAST_BUTTON_RECT = pg.Rect(WINDOW_SIZE - 160, _PANEL_TOP + 3, 150, 28)

_BANNER_COLORS = {"sunk": (255, 190, 60), "hit": (255, 90, 70), "miss": COLOR_WHITE, "cast": (200, 200, 60)}
_BANNER_DURATION_MS = 2200
_SPECIAL_BANNER_DURATION_MS = 4000  # specials get more screen time than a routine hit/miss
_BANNER_FADE_MS = 400
_REVEAL_DURATION_MS = 1000
_REVEAL_COLOR = (255, 60, 60, 130)

# Pakistan's "Accept/Refuse" modal -- centered over the board area the same
# way _draw_banner centers on (WINDOW_SIZE // 2, WINDOW_SIZE // 2), just
# bigger, since unlike the banner this one blocks input until answered.
_PAKISTAN_BOX_RECT = pg.Rect(WINDOW_SIZE // 2 - 220, WINDOW_SIZE // 2 - 70, 440, 140)
_PAKISTAN_ACCEPT_RECT = pg.Rect(WINDOW_SIZE // 2 - 170, WINDOW_SIZE // 2 + 10, 150, 40)
_PAKISTAN_REFUSE_RECT = pg.Rect(WINDOW_SIZE // 2 + 20, WINDOW_SIZE // 2 + 10, 150, 40)

# Specials whose payload needs an interactive target/geometry pick after
# clicking the cast button, rather than sending immediately with {} (like
# Congo/URSS and Phase 1's placeholder do). China is handled separately in
# _try_cast: it only enters picking mode for its Surveillance mode (viewing
# an opponent), not its self-targeting Counterfeit mode.
_TARGETED_SPECIALS = {"USA", "Italy"}

# Specials that target an opponent but need no geometry beyond "whichever
# board you're currently viewing" -- sent immediately on click, unlike
# _TARGETED_SPECIALS, which need a follow-up board click to aim.
_OPPONENT_TARGET_SPECIALS = {"Bresil"}


def _initial_window_size():
    """Fit the match window to the display on first open, so the bottom panel
    isn't spawned off-screen on shorter displays. The player can still resize
    the window afterwards -- see `MatchView._present`.
    """
    try:
        desktop_h = pg.display.get_desktop_sizes()[0][1]
    except (pg.error, IndexError):
        return WINDOW_SIZE, MATCH_WINDOW_HEIGHT
    scale = min(1.0, (desktop_h - 80) / MATCH_WINDOW_HEIGHT)  # headroom for window chrome
    return round(WINDOW_SIZE * scale), round(MATCH_WINDOW_HEIGHT * scale)


class MatchView:
    def __init__(self, window, conn, me, seats, my_grid):
        self.conn = conn
        self.me = me
        self.seats = seats
        self.my_grid = my_grid  # my own placed fleet, kept in sync with incoming hits
        self.state = None
        self.selected = me
        self._applied_hits = set()  # cells on my board already replayed into my_grid
        self._cursor_cell = None
        self._font = board_view.get_font()
        self._small_font = pg.font.Font(None, 20)  # tile captions
        self._banner_font = pg.font.Font(None, 32)
        self._banner = None  # (text, color, expires_at_tick, boat_name) or None
        self._my_country = seats[me]["country"]
        self._special_cost = SPECIAL_COSTS.get(self._my_country)
        self._cast_button = (
            Button(_CAST_BUTTON_RECT, f"Spécial ({self._special_cost})") if self._special_cost is not None else None
        )
        self._picking = False  # True while choosing a target/geometry for a _TARGETED_SPECIALS cast
        self._pick_axis = "row"  # Italy/China only: which axis the next click will target; R toggles it
        self._reveal = None  # China surveillance: {"target", "cells", "expires_at"} or None
        self._pakistan_prompt = None  # {"expires_at"} while I've been asked to Accept/Refuse, else None
        self._pakistan_accept_button = Button(_PAKISTAN_ACCEPT_RECT, "Accepter")
        self._pakistan_refuse_button = Button(_PAKISTAN_REFUSE_RECT, "Refuser")
        # The real window is resizable and only ever shows a scaled copy of
        # `canvas`, which stays fixed size so every draw call below keeps its
        # simple pixel math -- see `_present`/`_to_canvas` for the scale and
        # letterbox translation between the two.
        self.window = pg.display.set_mode(_initial_window_size(), pg.RESIZABLE)
        self.canvas = pg.Surface((WINDOW_SIZE, MATCH_WINDOW_HEIGHT)).convert()
        self._scale = 1.0
        self._offset = (0, 0)

    # --- main loop ---------------------------------------------------------

    def run(self):
        """Drive the match to its end. Returns the final `state` dict, or raises
        ConnectionError if the host drops (the caller shows a disconnect screen).
        """
        self._await_first_state()
        self.selected = self._first_opponent()
        while not self.state["over"]:
            for event in pg.event.get():
                quit_if_closed(event)
                self._handle_input(event)
            self._drain_messages()
            self.render()
            self._present()
            pg.time.wait(16)
        self.render()
        self._present()
        return self.state

    def _await_first_state(self):
        while self.state is None:
            for event in pg.event.get():
                quit_if_closed(event)
                self._handle_input(event)  # so a resize is honored while still waiting
            self._drain_messages()
            self.canvas.fill(COLOR_BLUE)
            board_view.draw_sea(self.canvas)
            self._draw_panel_text("En attente du début de la partie...", 20)
            self._present()
            pg.time.wait(16)

    def _drain_messages(self):
        while True:
            message = self.conn.poll()  # raises ConnectionError if the host drops
            if message is None:
                return
            kind = message.get("type")
            if kind == "state":
                self._apply_state(message)
            elif kind == "event":
                self._apply_event(message)
            elif kind == "reveal":
                self._apply_reveal(message)
            elif kind == "prompt":
                self._apply_prompt(message)

    def _apply_state(self, state):
        self.state = state
        if not self._my_turn():
            self._picking = False  # e.g. the match ended while we were mid-pick
        if self.selected != self.me and state["boards"][self.selected]["shielded"]:
            # The board we were looking at just vanished from our ribbon --
            # don't leave the view stuck on a now-hidden opponent.
            self.selected = self._first_opponent()
        for x, y, hit in state["boards"][self.me]["shots"]:
            if hit and (x, y) not in self._applied_hits:
                self.my_grid.register_shot((x, y))  # flips is_hit / retires sunk boats
                self._applied_hits.add((x, y))

    def _apply_event(self, event):
        color = _BANNER_COLORS[event["kind"]]
        duration = _SPECIAL_BANNER_DURATION_MS if event["kind"] == "cast" else _BANNER_DURATION_MS
        self._banner = (event["text"], color, pg.time.get_ticks() + duration, event.get("boat_name"))
        self._play_sound(event)
        special = event.get("special")
        if special in _TARGETED_SPECIALS and event["target"] == self.selected:
            self._play_special_animation(special, event)
        elif event["cell"] is not None and event["target"] == self.selected:
            # Show the burst on the board we're already looking at.
            play_impact_animation(self.canvas, self.render, [(tuple(event["cell"]), event["hit"])], present=self._present)
        revived = event.get("revived_cells")
        if revived and event["shooter"] == self.me:
            # Mirror a self-targeting revive (e.g. URSS/Congo) onto my own
            # locally tracked fleet -- the incremental hit-replay in
            # _apply_state has no way to undo a sink, so this is synced
            # explicitly instead.
            self.my_grid.revive_boat_with_cells([tuple(c) for c in revived])
        if special == "Bresil":
            self._apply_bresil_theft(event)
        elif special == "China" and event.get("mode") == "counterfeit" and event.get("placed") and event["shooter"] == self.me:
            # Mirror the new decoy onto my own locally tracked fleet -- same
            # "hit-replay can't add a whole boat" reason as Brésil's theft.
            boat = self.my_grid.add_boat([tuple(c) for c in event["cells"]], name=event["boat_name"])
            boat.hits_remaining = 1

    def _apply_bresil_theft(self, event):
        """Mirror a Brésil steal onto whichever of my own two locally tracked
        fleets it affects -- the incremental hit-replay in _apply_state has
        no way to add or remove a whole boat, so this is synced explicitly.
        """
        if event["shooter"] == self.me:
            self.my_grid.add_boat([tuple(c) for c in event["new_cells"]], name=event["boat_name"])
        elif event["target"] == self.me:
            cells = {tuple(c) for c in event["stolen_cells"]}
            for boat in list(self.my_grid.floating_boats):
                if {c for c, _ in boat.cells} == cells:
                    self.my_grid.remove_boat(boat)
                    return

    def _apply_reveal(self, message):
        self._reveal = {
            "target": message["target"],
            "cells": [tuple(c) for c in message["cells"]],
            "expires_at": pg.time.get_ticks() + _REVEAL_DURATION_MS,
        }

    def _apply_prompt(self, message):
        if message.get("kind") == "pakistan":
            self._pakistan_prompt = {"expires_at": pg.time.get_ticks() + message["deadline_ms"]}

    def _play_special_animation(self, special, event):
        cells = [tuple(c) for c in event["cells"]]
        hits = {tuple(c) for c in event["hits"]}
        if special == "USA":
            play_impact_animation(self.canvas, self.render, [(c, c in hits) for c in cells], present=self._present)
        elif special == "Italy":
            play_flyover_animation(self.canvas, self.render, cells, hits, present=self._present)

    def _play_sound(self, event):
        country = self.seats[event["shooter"]]["country"]
        if event["kind"] == "sunk":
            sound.play_sunk(country)
        elif event["kind"] == "hit":
            sound.play_hit(country)
        elif event["kind"] == "cast":
            sound.play_cast(country)
            sound.play_special(country)
        elif event["cell"] is not None:
            sound.play_miss(country)

    # --- input -------------------------------------------------------------

    def _handle_input(self, event):
        if event.type == pg.VIDEORESIZE:
            self.window = pg.display.set_mode(event.size, pg.RESIZABLE)
        elif event.type == pg.KEYDOWN:
            self._handle_key(event)
        elif event.type == pg.MOUSEMOTION:
            if self._in_canvas(event.pos):
                x, y = self._to_canvas(event.pos)
                cell = board_view.cell_from_pos((x, y))
                self._cursor_cell = cell if (y < _PANEL_TOP and board_view.in_bounds(*cell)) else None
            else:
                self._cursor_cell = None
        elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            if self._in_canvas(event.pos):
                pos = self._to_canvas(event.pos)
                if self._pakistan_prompt is not None:
                    self._handle_pakistan_click(pos)  # blocks every other click until answered
                elif _CAST_BUTTON_RECT.collidepoint(pos):
                    self._try_cast()
                elif pos[1] >= _PANEL_TOP:
                    self._select_from_panel(pos)
                elif self._picking:
                    self._submit_targeted_cast(pos)
                else:
                    self._try_fire(pos)

    def _handle_pakistan_click(self, pos):
        if _PAKISTAN_ACCEPT_RECT.collidepoint(pos):
            self._respond_to_pakistan("accept")
        elif _PAKISTAN_REFUSE_RECT.collidepoint(pos):
            self._respond_to_pakistan("refuse")

    def _respond_to_pakistan(self, choice):
        self.conn.send({"type": "respond", "choice": choice})
        self._pakistan_prompt = None

    def _handle_key(self, event):
        if not self._picking:
            return
        if event.key == pg.K_ESCAPE:
            self._picking = False
        elif event.key == pg.K_r and self._my_country in ("Italy", "China"):
            self._pick_axis = "col" if self._pick_axis == "row" else "row"

    def _select_from_panel(self, pos):
        for seat, rect in self._tile_rects():
            if self._tile_visible(seat) and rect.collidepoint(pos):
                self.selected = seat
                self._cursor_cell = None
                return

    def _try_fire(self, pos):
        cell = board_view.cell_from_pos(pos)
        if board_view.in_bounds(*cell) and self._can_fire(cell):
            self.conn.send({"type": "fire", "target": self.selected, "x": cell[0], "y": cell[1]})

    def _try_cast(self):
        if not self._can_cast():
            return
        if self._my_country == "China":
            if self.selected == self.me:  # Counterfeit: self-targeting, no geometry needed
                self.conn.send({"type": "cast", "payload": {"mode": "counterfeit"}})
            else:  # Surveillance: needs a follow-up board click to pick axis/half
                self._picking = True
                self._pick_axis = "row"
        elif self._my_country in _TARGETED_SPECIALS:
            self._picking = True
            self._pick_axis = "row"
        elif self._my_country in _OPPONENT_TARGET_SPECIALS:
            if self.selected != self.me:  # must be viewing an opponent's board to target them
                self.conn.send({"type": "cast", "payload": {"target": self.selected}})
        else:
            self.conn.send({"type": "cast", "payload": {}})

    def _submit_targeted_cast(self, pos):
        """Turn a board click while `_picking` into the targeted special's
        payload. Cancels picking either way -- an invalid pick (bad target,
        or a USA block that wouldn't fully fit) is just silently dropped,
        same as any other illegal action in this game.
        """
        self._picking = False
        cell = board_view.cell_from_pos(pos)
        if not board_view.in_bounds(*cell) or self.selected == self.me:
            return
        if self._my_country == "USA":
            if cell[0] + 3 >= BOARD_SIZE or cell[1] + 3 >= BOARD_SIZE:
                return  # the 4x4 block wouldn't fully fit -- see the Phase 2 plan
            payload = {"target": self.selected, "x": cell[0], "y": cell[1]}
        elif self._my_country == "Italy":
            index = cell[1] if self._pick_axis == "row" else cell[0]
            payload = {"target": self.selected, "axis": self._pick_axis, "index": index}
        elif self._my_country == "China":
            index = cell[1] if self._pick_axis == "row" else cell[0]
            half = "low" if index < BOARD_SIZE // 2 else "high"
            payload = {"target": self.selected, "mode": "surveillance", "axis": self._pick_axis, "half": half}
        else:
            return
        self.conn.send({"type": "cast", "payload": payload})

    def _can_fire(self, cell):
        return (
            self.state is not None
            and not self.state["over"]
            and self.state["turn"] == self.me
            and self.selected != self.me
            and self.state["boards"][self.selected]["alive"]
            and not self.state["boards"][self.selected]["shielded"]
            and cell not in self._shot_cells(self.selected)
        )

    def _can_cast(self):
        return (
            self._my_turn()
            and self._special_cost is not None
            and self.state["boards"][self.me]["energy"] >= self._special_cost
            and not self._usa_casts_exhausted()
        )

    def _usa_casts_exhausted(self):
        return self._my_country == "USA" and self.state["boards"][self.me]["usa_casts"] >= USA_MAX_CASTS

    # --- scaling: real (resizable) window <-> fixed-size canvas ------------

    def _present(self):
        """Scale `canvas` to fit the current window size, letterboxed to keep
        the board's aspect ratio, and flip. Updates `_scale`/`_offset` so
        `_to_canvas` can invert the mapping for mouse input.
        """
        win_w, win_h = self.window.get_size()
        scale = max(min(win_w / WINDOW_SIZE, win_h / MATCH_WINDOW_HEIGHT), 0.1)
        scaled_size = (round(WINDOW_SIZE * scale), round(MATCH_WINDOW_HEIGHT * scale))
        self._scale = scale
        self._offset = ((win_w - scaled_size[0]) // 2, (win_h - scaled_size[1]) // 2)
        self.window.fill(COLOR_BLACK)
        scaled = self.canvas if scaled_size == self.canvas.get_size() else pg.transform.smoothscale(self.canvas, scaled_size)
        self.window.blit(scaled, self._offset)
        pg.display.flip()

    def _in_canvas(self, pos):
        """Whether a real-window mouse position lands on the scaled canvas,
        as opposed to a letterbox bar."""
        ox, oy = self._offset
        sw, sh = round(WINDOW_SIZE * self._scale), round(MATCH_WINDOW_HEIGHT * self._scale)
        return ox <= pos[0] < ox + sw and oy <= pos[1] < oy + sh

    def _to_canvas(self, pos):
        """Map a real-window mouse position (already known to be `_in_canvas`)
        back to canvas-space pixel coordinates."""
        ox, oy = self._offset
        return int((pos[0] - ox) / self._scale), int((pos[1] - oy) / self._scale)

    # --- queries -----------------------------------------------------------

    def _my_turn(self):
        return self.state is not None and not self.state["over"] and self.state["turn"] == self.me

    def _first_opponent(self):
        for seat in range(len(self.seats)):
            board = self.state["boards"][seat]
            if seat != self.me and board["alive"] and not board["shielded"]:
                return seat
        for seat in range(len(self.seats)):  # everyone alive left is shielded -- pick one anyway
            if seat != self.me and self.state["boards"][seat]["alive"]:
                return seat
        return self.me

    def _shot_cells(self, seat):
        return {(x, y) for x, y, _ in self.state["boards"][seat]["shots"]}

    def _kills_of_me_by(self, seat):
        return sum(1 for s in self.state["sinks"] if s["by"] == seat and s["board"] == self.me)

    # --- rendering ---------------------------------------------------------

    def render(self):
        board_view.draw_sea(self.canvas)
        board_view.draw_grid_lines(self.canvas)
        if self.selected == self.me:
            self._draw_own_board()
        else:
            self._draw_opponent_board(self.selected)
        self._draw_panel()
        self._draw_picking_hint()
        self._draw_banner()
        self._draw_pakistan_prompt()

    def _draw_own_board(self):
        for boat in self.my_grid.floating_boats:
            board_view.draw_boat(self.canvas, boat)
        for boat in self.my_grid.sunk_boats:
            board_view.draw_boat(self.canvas, boat)

    def _draw_opponent_board(self, seat):
        board = self.state["boards"][seat]
        sunk_cells = {tuple(cell) for boat in board["sunk"] for cell in boat["cells"]}
        for x, y, hit in board["shots"]:
            if (x, y) in sunk_cells:
                continue  # drawn as part of the revealed sunk boat below
            board_view.draw_cross(self.canvas, COLOR_RED if hit else COLOR_BLACK, (x, y))
        for boat in board["sunk"]:
            cells = [tuple(cell) for cell in boat["cells"]]
            board_view.draw_boat(self.canvas, Boat.already_sunk(cells, name=boat["name"]))
        self._draw_reveal(seat)
        if self._cursor_cell is None or not self._my_turn() or not board["alive"] or board["shielded"]:
            return
        if self._picking:
            self._draw_targeting_preview()
        elif self._cursor_cell not in self._shot_cells(seat):
            board_view.draw_cross(self.canvas, COLOR_GREY, self._cursor_cell)

    def _targeted_cells(self):
        """The cells the current pick would affect if submitted right now
        (from `self._cursor_cell`), or None if the pick isn't valid there --
        used for both the live preview and (by _submit_targeted_cast) the
        actual cast payload's geometry.
        """
        x, y = self._cursor_cell
        if self._my_country == "USA":
            if x + 3 >= BOARD_SIZE or y + 3 >= BOARD_SIZE:
                return None
            return [(x + dx, y + dy) for dx in range(4) for dy in range(4)]
        if self._my_country == "Italy":
            if self._pick_axis == "row":
                return [(cx, y) for cx in range(BOARD_SIZE)]
            return [(x, cy) for cy in range(BOARD_SIZE)]
        if self._my_country == "China":
            index = y if self._pick_axis == "row" else x
            half = "low" if index < BOARD_SIZE // 2 else "high"
            lo, hi = (0, BOARD_SIZE // 2) if half == "low" else (BOARD_SIZE // 2, BOARD_SIZE)
            if self._pick_axis == "row":
                return [(cx, cy) for cy in range(lo, hi) for cx in range(BOARD_SIZE)]
            return [(cx, cy) for cx in range(lo, hi) for cy in range(BOARD_SIZE)]
        return None

    def _draw_targeting_preview(self):
        for cell in self._targeted_cells() or []:
            board_view.draw_preview_highlight(self.canvas, cell)

    def _draw_reveal(self, seat):
        """China's surveillance: briefly overlay spotted ship cells on the
        board they belong to. Client-side timer only -- the server already
        sent this once, privately, and won't repeat it.
        """
        if self._reveal is None:
            return
        if pg.time.get_ticks() >= self._reveal["expires_at"]:
            self._reveal = None
            return
        if self._reveal["target"] != seat:
            return
        for cell in self._reveal["cells"]:
            board_view.draw_preview_highlight(self.canvas, cell, color=_REVEAL_COLOR)

    # --- panel -------------------------------------------------------------

    def _tile_rects(self):
        n = len(self.seats)
        tile_w = WINDOW_SIZE // n
        return [(seat, pg.Rect(seat * tile_w, _TILE_TOP, tile_w, _MINI + 3 * _CAPTION_STEP + 6)) for seat in range(n)]

    def _tile_visible(self, seat):
        """A shielded player's tile disappears from everyone else's ribbon --
        Congo's "fully immune, cannot be targeted" extends to not even being
        visible -- but stays visible (with the shield marker) in their own.
        """
        return seat == self.me or not self.state["boards"][seat]["shielded"]

    def _draw_panel(self):
        pg.draw.rect(self.canvas, COLOR_DARK_GREY, (0, _PANEL_TOP, WINDOW_SIZE, MATCH_WINDOW_HEIGHT - _PANEL_TOP))
        self._draw_turn_line()
        self._draw_cast_button()
        for seat, rect in self._tile_rects():
            if self._tile_visible(seat):
                self._draw_tile(seat, rect)

    def _draw_turn_line(self):
        if self._my_turn():
            text = "À VOUS de jouer"
            if self.state["extra"]:
                text += "  —  TIR BONUS ! (touché : rejouez)"
            color = _HIGHLIGHT
        elif self.state["over"]:
            text, color = "Partie terminée", COLOR_WHITE
        else:
            text, color = f"Tour de {self.seats[self.state['turn']]['name']}", COLOR_WHITE
        self.canvas.blit(self._font.render(text, True, color), (10, _PANEL_TOP + 6))

    def _draw_cast_button(self):
        if self._cast_button is None:
            return
        self._cast_button.draw(self.canvas, self._small_font, selected=self._can_cast())
        board_view.draw_energy_icon(self.canvas, (_CAST_BUTTON_RECT.right - 20, _CAST_BUTTON_RECT.y + 7), size=14)
        hint_text = self._cast_hint_text()
        if hint_text is not None:
            hint = self._small(hint_text, COLOR_WHITE)
            self.canvas.blit(hint, (_CAST_BUTTON_RECT.left - hint.get_width() - 8, _CAST_BUTTON_RECT.centery - hint.get_height() // 2))

    def _cast_hint_text(self):
        """Why the cast button is greyed out right now, beyond "not enough
        energy" (which the button's own selected/unselected look already
        conveys) -- or None if there's nothing extra worth explaining.
        """
        if self._my_country == "Congo" and self.state["boards"][self.me]["congo_cooldown"]:
            return "disponible au prochain tour"
        if self._usa_casts_exhausted():
            return f"déjà utilisé {USA_MAX_CASTS}/{USA_MAX_CASTS} fois"
        return None

    def _draw_tile(self, seat, rect):
        board = self.state["boards"][seat]
        mini = pg.Rect(rect.centerx - _MINI // 2, rect.y, _MINI, _MINI)
        self._draw_mini_board(mini, seat)
        if seat == self.selected:
            pg.draw.rect(self.canvas, _HIGHLIGHT, mini, 3)
        name = self.seats[seat]["name"] + (" (vous)" if seat == self.me else "")
        name = name if board["alive"] else name + " (éliminé)"
        color = COLOR_WHITE if board["alive"] else COLOR_GREY
        y = mini.bottom + 3
        name_surface = self._small(name, color)
        self.canvas.blit(name_surface, (rect.x + 6, y))
        if board["shielded"]:
            board_view.draw_shield_icon(self.canvas, (rect.x + 6 + name_surface.get_width() + 5, y + 1), size=13)
        y += _CAPTION_STEP
        score_line = f"{board['score']} pt · {board['ships_left']} nav · a coulé {self._kills_of_me_by(seat)}"
        self.canvas.blit(self._small(score_line, color), (rect.x + 6, y))
        y += _CAPTION_STEP
        energy_surface = self._small(str(board["energy"]), color)
        self.canvas.blit(energy_surface, (rect.x + 6, y))
        board_view.draw_energy_icon(self.canvas, (rect.x + 6 + energy_surface.get_width() + 5, y + 2), size=12)

    def _draw_mini_board(self, rect, seat):
        board = self.state["boards"][seat]
        pg.draw.rect(self.canvas, _SEA if board["alive"] else COLOR_GREY, rect)
        cell = rect.width / BOARD_SIZE
        sunk_cells = {tuple(c) for boat in board["sunk"] for c in boat["cells"]}
        for x, y, hit in board["shots"]:
            if (x, y) in sunk_cells:
                continue
            color = COLOR_RED if hit else COLOR_BLACK
            pg.draw.rect(self.canvas, color, (rect.x + x * cell, rect.y + y * cell, cell, cell))
        for cx, cy in sunk_cells:
            pg.draw.rect(self.canvas, (120, 20, 20), (rect.x + cx * cell, rect.y + cy * cell, cell, cell))
        pg.draw.rect(self.canvas, COLOR_BLACK, rect, 1)

    def _draw_banner(self):
        if self._banner is None:
            return
        text, color, expires_at, boat_name = self._banner
        remaining = expires_at - pg.time.get_ticks()
        if remaining <= 0:
            self._banner = None
            return
        alpha = 255 if remaining > _BANNER_FADE_MS else round(255 * remaining / _BANNER_FADE_MS)
        segments = self._banner_segments(text, color, boat_name)
        surfaces = [self._banner_font.render(segment, True, segment_color) for segment, segment_color in segments]
        total_width = sum(s.get_width() for s in surfaces)
        height = surfaces[0].get_height()
        box = pg.Surface((total_width + 40, height + 24), pg.SRCALPHA)
        box.fill((0, 0, 0, 190))
        x = 20
        for surface in surfaces:
            box.blit(surface, (x, 12))
            x += surface.get_width()
        box.set_alpha(alpha)
        self.canvas.blit(box, box.get_rect(center=(WINDOW_SIZE // 2, WINDOW_SIZE // 2)))

    def _banner_segments(self, text, color, boat_name):
        """Split `text` around `boat_name` so the ship's name can be rendered
        in the highlight color while the rest of the banner keeps its normal
        per-kind color -- or the whole text as one segment if there's no boat
        name to highlight (a miss, or a special with no ship involved).
        """
        if not boat_name or boat_name not in text:
            return [(text, color)]
        before, _, after = text.partition(boat_name)
        return [(before, color), (boat_name, _HIGHLIGHT), (after, color)]

    def _draw_pakistan_prompt(self):
        if self._pakistan_prompt is None:
            return
        remaining_ms = self._pakistan_prompt["expires_at"] - pg.time.get_ticks()
        if remaining_ms <= 0:
            self._pakistan_prompt = None  # ran out locally -- the server times it out as an Accept regardless
            return
        overlay = pg.Surface((WINDOW_SIZE, MATCH_WINDOW_HEIGHT), pg.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.canvas.blit(overlay, (0, 0))
        pg.draw.rect(self.canvas, COLOR_DARK_GREY, _PAKISTAN_BOX_RECT)
        pg.draw.rect(self.canvas, COLOR_WHITE, _PAKISTAN_BOX_RECT, 2)
        title = self._font.render(f"Offre du Cousin à Dubaï ! ({remaining_ms // 1000 + 1}s)", True, COLOR_WHITE)
        self.canvas.blit(title, title.get_rect(center=(_PAKISTAN_BOX_RECT.centerx, _PAKISTAN_BOX_RECT.y + 30)))
        self._pakistan_accept_button.draw(self.canvas, self._small_font, selected=True)
        self._pakistan_refuse_button.draw(self.canvas, self._small_font, selected=True)

    def _draw_picking_hint(self):
        if not self._picking:
            return
        if self._my_country == "Italy":
            axis_label = "ligne" if self._pick_axis == "row" else "colonne"
            text = f"Bombardiro : cliquez une case ({axis_label} -- R pour changer, Échap pour annuler)"
        elif self._my_country == "China":
            axis_label = "lignes" if self._pick_axis == "row" else "colonnes"
            text = f"Surveillance : cliquez une case (moitié en {axis_label} -- R pour changer, Échap pour annuler)"
        else:
            text = "Test nucléaire : cliquez le coin haut-gauche de la zone 4x4 (Échap pour annuler)"
        surface = self._small_font.render(text, True, _HIGHLIGHT)
        self.canvas.blit(surface, surface.get_rect(center=(WINDOW_SIZE // 2, 20)))

    def _draw_panel_text(self, text, y):
        self.canvas.blit(self._font.render(text, True, COLOR_WHITE), (10, _PANEL_TOP + y))

    def _small(self, text, color):
        return self._small_font.render(text, True, color)
