"""Authoritative game state for N-player free-targeting LAN battleship.

Pure rules only -- no pygame, no sockets -- so it can be unit-tested directly
and driven by network/server.py as the single source of truth for a match.

Free targeting: on your turn you pick ANY living opponent and ANY un-shot cell
on their board. A hit lets you shoot again (possibly at a different player); a
miss passes the turn. Scoring is sinks-only: +SINK_POINTS per ship, +KILL_BONUS
instead when the sink eliminates a player. First to WIN_SCORE, or the last
player standing, wins. See SPEC-multiplayer.txt.

Seats are fixed for the whole match: eliminated players are marked dead and
skipped, never removed, so seat indices stay stable (turn order never shifts).
"""

from dataclasses import dataclass

from ..config import ENERGY_PASSIVE_GAIN, ENERGY_RETALIATION_GAIN, KILL_BONUS, SINK_POINTS, SPECIAL_COSTS, WIN_SCORE
from ..models.grid import Grid
from .specials import HANDLERS, resolve_pakistan_outcome


@dataclass
class Outcome:
    """Result of a single resolve_shot call, consumed by the server to build
    the public event/state broadcast.
    """

    valid: bool
    shooter: int
    target: int = -1
    cell: tuple = None
    hit: bool = False
    sunk_boat: object = None
    boat_name: str = None
    eliminated: bool = False  # the target lost their last ship on this shot
    extra: bool = False  # the shooter earned an immediate extra shot
    over: bool = False  # this shot ended the match
    reason: str = None  # set only when valid is False


@dataclass
class CellResult:
    """Result of applying one shot to one already-validated (target, cell)
    pair -- the per-cell counterpart shared by a normal shot and every
    multi-cell special (USA's block, Italy's row/column). Callers are
    responsible for turn/win-check/extra-shot logic afterward.
    """

    hit: bool
    sunk_boat: object = None
    boat_name: str = None
    eliminated: bool = False  # the target lost their last ship on this cell


@dataclass
class CastOutcome:
    """Result of a single resolve_cast call -- the special-cast counterpart to
    Outcome. A cast never grants a bonus shot, no matter its effect, so
    (unlike Outcome) there is no `extra` field. `effect` is whatever extra,
    special-specific data the country's handler returned (e.g. which cells
    were hit), merged into the public event broadcast by the server.
    """

    valid: bool
    shooter: int
    special: str = None
    cost: int = 0
    over: bool = False
    effect: dict = None
    reason: str = None  # set only when valid is False


class Skirmish:
    def __init__(self, players, win_score=WIN_SCORE, sink_points=SINK_POINTS, kill_bonus=KILL_BONUS):
        self.players = list(players)  # each a Player with an already-placed Grid
        self.alive = [True] * len(self.players)
        self.shots = [{} for _ in self.players]  # seat -> {(x, y): hit_bool} landed on that board
        self.sink_log = []  # [{"by": seat, "board": seat, "boat": name, "at": action_count}] in order
        self.special_state = [{} for _ in self.players]  # per-seat scratch dict, owned by engine/specials.py handlers
        self.action_count = 0  # monotonic count of resolved actions, for specials like URSS's "since last turn"
        self.turn_start_count = [0] * len(self.players)  # action_count as of each seat's most recently STARTED turn
        self.turn = 0
        self.extra = False  # is the current turn a bonus shot?
        self.win_score = win_score
        self.sink_points = sink_points
        self.kill_bonus = kill_bonus

    # --- queries -----------------------------------------------------------

    def living_seats(self):
        return [i for i, alive in enumerate(self.alive) if alive]

    @property
    def winner(self):
        """The winning seat index, or None while the match is still going."""
        living = self.living_seats()
        if len(living) <= 1:
            return living[0] if living else self._highest_scorer()
        if max(player.score for player in self.players) >= self.win_score:
            return self._highest_scorer()
        return None

    @property
    def is_over(self):
        return self.winner is not None

    def _highest_scorer(self):
        return max(range(len(self.players)), key=lambda i: self.players[i].score)

    # --- turn resolution ---------------------------------------------------

    def resolve_shot(self, shooter, target, cell):
        """Validate and apply one shot. Invalid shots return an Outcome with
        valid=False and DO NOT consume the turn or mutate any state.
        """
        reason = self._reject(shooter, target, cell)
        if reason is not None:
            return Outcome(valid=False, shooter=shooter, target=target, cell=cell, reason=reason)

        # Passive gain and the "start of turn" bookkeeping happen once per
        # turn, not on a chained bonus shot (self.extra means this action
        # continues the same turn as the hit that granted it).
        if not self.extra:
            self.players[shooter].energy += ENERGY_PASSIVE_GAIN
            self._mark_turn_started(shooter)

        result = self._apply_cell(shooter, target, cell)

        # Win is checked BEFORE granting the extra shot: a kill that ends the
        # match must not hand the shooter a shot in an already-over game.
        over = self.is_over
        extra = False
        if not over:
            if result.hit:
                extra = True  # same shooter fires again; turn stays put
            else:
                self._advance_turn()
        self.extra = extra
        self.action_count += 1

        return Outcome(
            valid=True,
            shooter=shooter,
            target=target,
            cell=cell,
            hit=result.hit,
            sunk_boat=result.sunk_boat,
            boat_name=result.boat_name,
            eliminated=result.eliminated,
            extra=extra,
            over=over,
        )

    def _apply_cell(self, shooter, target, cell):
        """Apply one shot to one already-validated (target, cell) pair:
        updates the grid/shots/retaliation-energy/score/elimination
        bookkeeping shared by a normal shot and every multi-cell special.
        Does NOT check turn/bounds/already-shot (callers must have already
        validated that) and does NOT touch turn-advance/extra/action_count --
        a multi-cell special calls this once per cell, then the caller
        performs a single win-check/turn-advance after all cells resolve.
        """
        hit, sunk_boat = self.players[target].grid.register_shot(cell)
        self.shots[target][cell] = hit
        if hit:
            self.players[target].energy += ENERGY_RETALIATION_GAIN

        eliminated = False
        # Named whenever a boat was actually hit -- not just on a sink -- so
        # the announcement can say which ship, even for a plain hit. Grid's
        # own return value only distinguishes "sunk" from "not sunk" (and stays
        # that way -- the older hotseat engine shares register_shot and treats
        # a non-None second value as "this was a sink"), so a non-sunk hit's
        # boat is looked up separately here rather than changing that contract.
        boat_name = None
        if hit:
            if sunk_boat is not None:
                boat_name = sunk_boat.name
            else:
                boat_name = next(
                    (b.name for b in self.players[target].grid.floating_boats if any(c == cell for c, _ in b.cells)),
                    None,
                )
        if sunk_boat is not None:
            self.sink_log.append({"by": shooter, "board": target, "boat": boat_name, "at": self.action_count})
            if not self.players[target].grid.floating_boats:  # that was their last ship
                self.players[shooter].score += self.kill_bonus
                self.alive[target] = False
                eliminated = True
            else:
                self.players[shooter].score += self.sink_points

        return CellResult(hit=hit, sunk_boat=sunk_boat, boat_name=boat_name, eliminated=eliminated)

    def _mark_turn_started(self, shooter):
        """Bookkeeping for the start of a genuinely new turn (not a chained
        bonus shot), shared by resolve_shot and resolve_cast (each of which
        grants the passive energy gain itself, since resolve_cast needs the
        pending amount for its affordability check first). Advances the
        per-seat turn-start marker (for specials like URSS's "since my last
        turn") and lets the shooter's own country handler react -- e.g.
        Congo's shield/cooldown expiring exactly when its owner's turn comes
        back around.
        """
        self.turn_start_count[shooter] = self.action_count
        handler = HANDLERS.get(self.players[shooter].country)
        if handler is not None:
            handler.on_turn_start(self, shooter)

    def resolve_cast(self, shooter, payload=None):
        """Validate and apply one special cast, which replaces the shooter's
        normal shot for this turn. Invalid casts return valid=False and
        mutate nothing, same contract as resolve_shot. A cast never grants a
        bonus shot, regardless of its effect.
        """
        payload = payload or {}
        reason = self._reject_turn(shooter)
        if reason is not None:
            return CastOutcome(valid=False, shooter=shooter, reason=reason)

        country = self.players[shooter].country
        cost = SPECIAL_COSTS.get(country)
        if cost is None:
            return CastOutcome(valid=False, shooter=shooter, reason="unknown special")

        handler = HANDLERS[country]
        reason = handler.eligible(self, shooter, payload)
        if reason is not None:
            return CastOutcome(valid=False, shooter=shooter, special=country, reason=reason)

        # Same "not on a chained bonus shot" rule as resolve_shot's passive
        # gain, and spendable in the same turn it's granted.
        pending_gain = 0 if self.extra else ENERGY_PASSIVE_GAIN
        if self.players[shooter].energy + pending_gain < cost:
            return CastOutcome(valid=False, shooter=shooter, special=country, reason="not enough energy")

        self.players[shooter].energy += pending_gain
        self.players[shooter].energy -= cost
        if not self.extra:
            self._mark_turn_started(shooter)
        effect = handler.apply(self, shooter, payload) or {}

        if effect.get("deferred"):
            # Pakistan only: its consequences need input (every participant's
            # Accept/Refuse) that doesn't exist yet -- the turn-advance/win-check
            # below is postponed until resolve_pakistan_vote runs them instead,
            # once network/server.py has collected that input.
            return CastOutcome(valid=True, shooter=shooter, special=country, cost=cost, over=self.is_over, effect=effect)

        over = self.is_over
        self.extra = False  # casting never grants a bonus shot
        if not over:
            self._advance_turn()
        self.action_count += 1

        return CastOutcome(valid=True, shooter=shooter, special=country, cost=cost, over=over, effect=effect)

    def resolve_pakistan_vote(self, shooter, refused, accepted_order):
        """Apply Pakistan's Ponzi outcome and perform the turn-advance/win-check
        a normal resolve_cast would have done immediately -- deferred until now
        because it depends on every participant's Accept/Refuse response, which
        only network/server.py's _run_pakistan_vote (this method's sole caller)
        can collect. `refused`/`accepted_order` are seat lists; accepted_order
        is chronological (explicit accepts, then timeouts, in that order) since
        only its last entry suffers the Ponzi loss.
        """
        resolve_pakistan_outcome(self, shooter, refused, accepted_order)

        over = self.is_over
        self.extra = False
        if not over:
            self._advance_turn()
        self.action_count += 1
        return over

    def _reject_turn(self, shooter):
        """The subset of _reject's checks shared with resolve_cast."""
        if self.is_over:
            return "game over"
        if shooter != self.turn:
            return "not your turn"
        return None

    def _reject(self, shooter, target, cell):
        """Return a rejection reason string, or None if the shot is legal."""
        reason = self._reject_turn(shooter)
        if reason is not None:
            return reason
        if not (0 <= target < len(self.players)):
            return "no such target"
        if target == shooter:
            return "cannot target yourself"
        if not self.alive[target]:
            return "target already eliminated"
        if self.special_state[target].get("congo_shielded"):
            return "target is shielded"
        if not Grid.in_bounds(*cell):
            return "out of bounds"
        if cell in self.shots[target]:
            return "already shot there"
        return None

    def _advance_turn(self):
        n = len(self.players)
        for step in range(1, n + 1):
            candidate = (self.turn + step) % n
            if self.alive[candidate]:
                self.turn = candidate
                return

    def eliminate(self, seat):
        """Knock a player out without a killing shot (e.g. they disconnected).
        Their score is frozen, not voided, and if it was their turn it passes on.
        """
        if not self.alive[seat]:
            return
        self.alive[seat] = False
        self.extra = False
        if self.turn == seat and not self.is_over:
            self._advance_turn()

    # --- serialization -----------------------------------------------------

    def public_snapshot(self):
        """Everything that is public to every player (and spectators). Notably
        does NOT include afloat ship positions -- only shots taken, revealed
        sunk ships, and the aggregate counters. Identical for all recipients;
        each client overlays its own known ship positions for its own board.
        """
        winner = self.winner
        return {
            "turn": self.turn,
            "extra": self.extra,
            "over": self.is_over,
            "winner": winner,
            "sinks": list(self.sink_log),
            "boards": [self._board_snapshot(seat) for seat in range(len(self.players))],
        }

    def _board_snapshot(self, seat):
        player = self.players[seat]
        return {
            "owner": player.name,
            "country": player.country,
            "score": player.score,
            "energy": player.energy,
            "shielded": self.special_state[seat].get("congo_shielded", False),
            "congo_cooldown": self.special_state[seat].get("congo_cooldown", False),
            "usa_casts": self.special_state[seat].get("usa_casts", 0),
            "alive": self.alive[seat],
            "ships_left": len(player.grid.floating_boats),
            "shots": [[x, y, hit] for (x, y), hit in self.shots[seat].items()],
            "sunk": [
                {"cells": [list(cell) for cell, _ in boat.cells], "name": boat.name}
                for boat in player.grid.sunk_boats
            ],
        }
