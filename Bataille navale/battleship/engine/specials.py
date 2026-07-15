"""Per-country special-cast effect handlers, registered by country name.

Every country is registered from day one so a missing entry is a loud
KeyError during development, not a silent no-op. Phase 1 shipped one
placeholder (_always_eligible / _no_effect) for all seven countries; Phase 2
replaces USA/Italy/URSS with real handlers below. Later phases replace the
remaining entries; they never touch Skirmish.resolve_cast itself.

A handler's `eligible(skirmish, shooter, payload)` runs read-only, before any
energy is spent -- it may reject on payload shape/target validity as well as
country-specific gates (USA's cast cap, URSS's "sunk since last turn").
`apply(skirmish, shooter, payload)` runs only once eligibility AND cost have
both passed, and may return a dict of extra fields merged into the public
cast event broadcast (e.g. which cells were affected), so the client can
drive the special's own animation/effects.
"""

import random

from ..config import BOARD_SIZE, COUNTRIES, PAKISTAN_OFFER_TEXTS, PAKISTAN_REFUSAL_HITS, USA_MAX_CASTS
from ..models.boat import Boat


def _no_turn_start_hook(skirmish, seat):
    return None


class SpecialHandler:
    def __init__(self, eligible, apply, on_turn_start=None):
        self.eligible = eligible  # (skirmish, shooter, payload) -> reason:str|None
        self.apply = apply  # (skirmish, shooter, payload) -> dict|None
        # (skirmish, seat) -> None. Called for a country's own players at the
        # start of each of THEIR OWN genuinely new turns (not a chained bonus
        # shot) -- e.g. Congo's shield/cooldown expiring exactly when its
        # owner's turn comes back around. Most specials don't need this.
        self.on_turn_start = on_turn_start or _no_turn_start_hook


def _always_eligible(skirmish, shooter, payload):
    return None


def _no_effect(skirmish, shooter, payload):
    return None


HANDLERS = {country: SpecialHandler(_always_eligible, _no_effect) for country in COUNTRIES}


# --- shared helpers ----------------------------------------------------


def _valid_opponent(skirmish, shooter, target):
    if target is None or not (0 <= target < len(skirmish.players)):
        return "invalid target"
    if target == shooter:
        return "cannot target yourself"
    if not skirmish.alive[target]:
        return "target already eliminated"
    if skirmish.special_state[target].get("congo_shielded"):
        return "target is shielded"
    return None


def _apply_cells(skirmish, shooter, target, cells):
    """Apply `cells` to `target`'s board, silently skipping any cell already
    shot (an area effect isn't a precise single shot -- overlap is expected
    and shouldn't waste part of the cast). Returns the cells actually hit.
    """
    hits = []
    for cell in cells:
        if cell in skirmish.shots[target]:
            continue
        result = skirmish._apply_cell(shooter, target, cell)
        if result.hit:
            hits.append(list(cell))
    return hits


# --- USA: "Accidental Nuclear Test" -- a 4x4 block, max 2 casts/game ----


def _usa_cells(payload):
    x0, y0 = payload["x"], payload["y"]
    return [(x0 + dx, y0 + dy) for dx in range(4) for dy in range(4)]


def _usa_eligible(skirmish, shooter, payload):
    if skirmish.special_state[shooter].get("usa_casts", 0) >= USA_MAX_CASTS:
        return "already cast twice this game"
    target = payload.get("target")
    reason = _valid_opponent(skirmish, shooter, target)
    if reason is not None:
        return reason
    x, y = payload.get("x"), payload.get("y")
    if x is None or y is None:
        return "missing coordinates"
    if not (0 <= x and x + 3 < BOARD_SIZE and 0 <= y and y + 3 < BOARD_SIZE):
        return "out of bounds"
    return None


def _usa_apply(skirmish, shooter, payload):
    skirmish.special_state[shooter]["usa_casts"] = skirmish.special_state[shooter].get("usa_casts", 0) + 1
    target = payload["target"]
    cells = _usa_cells(payload)
    hits = _apply_cells(skirmish, shooter, target, cells)
    return {"target": target, "cells": [list(c) for c in cells], "hits": hits}


# --- Italy: "Bombardiro Crocodilo" -- a full row or column --------------


def _italy_cells(payload):
    axis, index = payload["axis"], payload["index"]
    if axis == "row":
        return [(x, index) for x in range(BOARD_SIZE)]
    return [(index, y) for y in range(BOARD_SIZE)]


def _italy_eligible(skirmish, shooter, payload):
    target = payload.get("target")
    reason = _valid_opponent(skirmish, shooter, target)
    if reason is not None:
        return reason
    axis, index = payload.get("axis"), payload.get("index")
    if axis not in ("row", "col") or index is None:
        return "missing axis/index"
    if not (0 <= index < BOARD_SIZE):
        return "out of bounds"
    return None


def _italy_apply(skirmish, shooter, payload):
    target = payload["target"]
    cells = _italy_cells(payload)
    hits = _apply_cells(skirmish, shooter, target, cells)
    return {
        "target": target,
        "cells": [list(c) for c in cells],
        "hits": hits,
        "axis": payload["axis"],
    }


# --- URSS: "Propagande" -- restore a ship sunk since your last turn -----


def _urss_eligible(skirmish, shooter, payload):
    grid = skirmish.players[shooter].grid
    if not grid.sunk_boats:
        return "no sunk ship to restore"
    threshold = skirmish.turn_start_count[shooter]
    recent = any(e["board"] == shooter and e["at"] >= threshold for e in skirmish.sink_log)
    if not recent:
        return "no ship of yours was sunk since your last turn"
    return None


def _urss_apply(skirmish, shooter, payload):
    grid = skirmish.players[shooter].grid
    cells = [cell for cell, _ in grid.sunk_boats[-1].cells]  # most recently sunk
    grid.revive_boat_with_cells(cells)
    for cell in cells:
        skirmish.shots[shooter].pop(cell, None)  # so it can be shot (and sunk) again
    return {"revived_cells": [list(c) for c in cells]}


# --- Congo: "Panne de Courant" -- shield + fragile revive, no back-to-back -


def _congo_eligible(skirmish, shooter, payload):
    if skirmish.special_state[shooter].get("congo_cooldown"):
        return "cannot cast two turns in a row"
    return None


def _congo_apply(skirmish, shooter, payload):
    skirmish.special_state[shooter]["congo_shielded"] = True
    skirmish.special_state[shooter]["congo_cooldown"] = True
    grid = skirmish.players[shooter].grid
    if not grid.sunk_boats:
        return {}  # the shield still applies -- the revive is just a no-op bonus here
    cells = [cell for cell, _ in grid.sunk_boats[-1].cells]  # most recently sunk
    boat = grid.revive_boat_with_cells(cells)
    boat.hits_remaining = 1  # fragile: destroyed again on a single hit, unlike URSS's full restore
    for cell in cells:
        skirmish.shots[shooter].pop(cell, None)  # so it can be shot (and re-sunk) again
    return {"revived_cells": [list(c) for c in cells]}


def _congo_on_turn_start(skirmish, seat):
    skirmish.special_state[seat]["congo_shielded"] = False
    skirmish.special_state[seat]["congo_cooldown"] = False


# --- Brésil: "Je te le rends demain" -- steal a random floating boat -------


def _bresil_eligible(skirmish, shooter, payload):
    return _valid_opponent(skirmish, shooter, payload.get("target"))


def _bresil_apply(skirmish, shooter, payload):
    target = payload["target"]
    target_grid = skirmish.players[target].grid
    boat = random.choice(target_grid.floating_boats)
    old_cells = [cell for cell, _ in boat.cells]
    target_grid.remove_boat(boat)
    eliminated = not target_grid.floating_boats  # stealing their last ship is still a kill
    if eliminated:
        skirmish.eliminate(target)
    skirmish.players[shooter].grid.add_boat_at_random_position(boat)
    new_cells = [cell for cell, _ in boat.cells]

    shooter_name = skirmish.players[shooter].name
    target_name = skirmish.players[target].name
    text = f"{shooter_name} a emprunté le {boat.name} de {target_name}, à rendre au tour prochain !"
    if eliminated:
        text += f" {target_name} n'a plus aucun navire !"

    return {
        "target": target,
        "boat_name": boat.name,
        "stolen_cells": [list(c) for c in old_cells],
        "new_cells": [list(c) for c in new_cells],
        "eliminated": eliminated,
        "text": text,
    }


# --- China: "Contrefaçon" -- counterfeit decoy, or peek at half a board -----

# China's cast button branches on which board the client currently has
# selected (see ui/match_view.py's _try_cast): viewing your own board casts
# Counterfeit, viewing an opponent's casts Surveillance. Both share one
# Energy cost and one country entry -- the registry avoids branching *across*
# countries, not within one country's own two modes.


def _china_half_cells(axis, half):
    lo, hi = (0, BOARD_SIZE // 2) if half == "low" else (BOARD_SIZE // 2, BOARD_SIZE)
    if axis == "row":
        return [(x, y) for y in range(lo, hi) for x in range(BOARD_SIZE)]
    return [(x, y) for x in range(lo, hi) for y in range(BOARD_SIZE)]


def _china_eligible(skirmish, shooter, payload):
    mode = payload.get("mode")
    if mode == "counterfeit":
        return None
    if mode == "surveillance":
        reason = _valid_opponent(skirmish, shooter, payload.get("target"))
        if reason is not None:
            return reason
        if payload.get("axis") not in ("row", "col") or payload.get("half") not in ("low", "high"):
            return "missing axis/half"
        return None
    return "unknown mode"


def _china_counterfeit_apply(skirmish, shooter):
    grid = skirmish.players[shooter].grid
    original = random.choice(grid.floating_boats)
    decoy = Boat(original.size, [(0, 0)] * original.size, name=f"Contrefaçon ({original.type})")
    decoy.hits_remaining = 1  # fragile: one hit reveals and sinks the fake, unlike a real ship
    placed = grid.add_boat_at_random_position(decoy)
    shooter_name = skirmish.players[shooter].name
    effect = {
        "mode": "counterfeit",
        "placed": placed,
        "text": f"{shooter_name} a fabriqué un faux navire pour tromper l'ennemi."
        if placed
        else f"{shooter_name} n'a plus de place pour une contrefaçon !",
    }
    if placed:
        cells = [cell for cell, _ in decoy.cells]
        for cell in cells:
            # add_boat_at_random_position only avoids cells occupied by a real
            # boat -- it can still land on water an opponent already shot at
            # (and missed) earlier in the game. Left alone, that cell would
            # stay permanently un-shootable ("already shot there"), making the
            # decoy impossible to ever pop and, if it were the only thing
            # still afloat, China unkillable. Clear it so it's live again,
            # same trick as Congo/URSS's revives.
            skirmish.shots[shooter].pop(cell, None)
        # Public, like Brésil's new_cells -- the decoy only works as a decoy if
        # it looks exactly like a real ship to everyone, so no privacy need here.
        effect["cells"] = [list(cell) for cell in cells]
        effect["boat_name"] = decoy.name
    return effect


def _china_surveillance_apply(skirmish, shooter, payload):
    target = payload["target"]
    axis, half = payload["axis"], payload["half"]
    cells = set(_china_half_cells(axis, half))
    target_grid = skirmish.players[target].grid
    revealed = [list(cell) for boat in target_grid.floating_boats for cell, _ in boat.cells if cell in cells]
    shooter_name = skirmish.players[shooter].name
    target_name = skirmish.players[target].name
    return {
        "mode": "surveillance",
        "target": target,
        "axis": axis,
        "half": half,
        "text": f"{shooter_name} espionne une partie du plateau de {target_name}.",
        # Real ship positions must never reach the public broadcast (unlike
        # every other special's effect fields) -- the server pops "private"
        # out before broadcasting and sends it only to the caster instead.
        "private": {"target": target, "cells": revealed},
    }


def _china_apply(skirmish, shooter, payload):
    if payload["mode"] == "counterfeit":
        return _china_counterfeit_apply(skirmish, shooter)
    return _china_surveillance_apply(skirmish, shooter, payload)


# --- Pakistan: "Le Cousin à Dubaï" -- broadcast Ponzi vote, resolved later --

# The only special that needs input from players OTHER than the caster, so
# it can't resolve inside apply() like every other handler -- that would
# require blocking network I/O this pure engine layer never does. Instead
# _pakistan_apply just identifies participants and returns effect={
# "deferred": True, ...}; Skirmish.resolve_cast sees that flag and skips its
# usual turn-advance/win-check, leaving it for resolve_pakistan_outcome
# (below) once network/server.py's _run_pakistan_vote has collected every
# participant's Accept/Refuse (or timeout).


def _pakistan_participants(skirmish, shooter):
    return [
        seat
        for seat in range(len(skirmish.players))
        if seat != shooter and skirmish.alive[seat] and not skirmish.special_state[seat].get("congo_shielded")
    ]


def _pakistan_eligible(skirmish, shooter, payload):
    if not _pakistan_participants(skirmish, shooter):
        return "no valid opponent to prank"
    return None


def _pakistan_apply(skirmish, shooter, payload):
    participants = _pakistan_participants(skirmish, shooter)
    shooter_name = skirmish.players[shooter].name
    return {
        "deferred": True,
        "participants": participants,
        "text": random.choice(PAKISTAN_OFFER_TEXTS).format(shooter=shooter_name),
    }


def _pakistan_random_hits(skirmish, shooter, target, count=PAKISTAN_REFUSAL_HITS):
    available = [(x, y) for x in range(BOARD_SIZE) for y in range(BOARD_SIZE) if (x, y) not in skirmish.shots[target]]
    random.shuffle(available)
    for cell in available[:count]:
        skirmish._apply_cell(shooter, target, cell)


def _pakistan_sink_random_ship(skirmish, shooter, target):
    grid = skirmish.players[target].grid
    if not grid.floating_boats:
        return
    boat = random.choice(grid.floating_boats)
    for cell, is_hit in list(boat.cells):
        if not is_hit:
            skirmish._apply_cell(shooter, target, cell)


def resolve_pakistan_outcome(skirmish, shooter, refused, accepted_order):
    """Apply the Ponzi scheme's consequences once network/server.py's
    _run_pakistan_vote has collected every participant's response: each
    refuser takes PAKISTAN_REFUSAL_HITS hits on random un-shot cells of their
    own board (for "losing an opportunity"), and the LAST seat (chronologically)
    to accept -- explicitly or by timeout -- loses one random ship outright.
    Called directly by Skirmish.resolve_pakistan_vote, not through HANDLERS,
    since this doesn't fit the eligible/apply shape (its input only exists
    after the original cast already returned).
    """
    for target in refused:
        _pakistan_random_hits(skirmish, shooter, target)
    if accepted_order:
        _pakistan_sink_random_ship(skirmish, shooter, accepted_order[-1])


HANDLERS["USA"] = SpecialHandler(_usa_eligible, _usa_apply)
HANDLERS["Italy"] = SpecialHandler(_italy_eligible, _italy_apply)
HANDLERS["URSS"] = SpecialHandler(_urss_eligible, _urss_apply)
HANDLERS["Congo"] = SpecialHandler(_congo_eligible, _congo_apply, on_turn_start=_congo_on_turn_start)
HANDLERS["Bresil"] = SpecialHandler(_bresil_eligible, _bresil_apply)
HANDLERS["China"] = SpecialHandler(_china_eligible, _china_apply)
HANDLERS["Pakistan"] = SpecialHandler(_pakistan_eligible, _pakistan_apply)
