"""Authoritative host for a free-targeting LAN match.

Runs in a background thread on the host machine. It owns the one true
`Skirmish` game state; every client (including the host's own player, wired in
through an in-process loopback) is a thin view that sends `fire` intents and
renders the `state`/`event` broadcasts this server sends back. Clients are
never trusted to resolve their own shots -- the server validates and applies
everything, so there is a single source of truth for turn order, scoring and
the win condition.

Protocol (newline-JSON, framed by connection.Connection):
    client -> server : join {name, country}   (read during the lobby, not here)
                       ready {boats:[{cells, name}]}
                       fire  {target, x, y}
                       cast  {payload: {...}}   (payload shape is special-specific; see
                                                 engine/specials.py for each country's shape)
                       respond {choice: "accept"|"refuse"}
                                (Pakistan's vote only, sent by a prompted participant)
    server -> client : roster {seats:[{name, country}], you}
                       place  {}
                       state  {...Skirmish.public_snapshot()...}
                       event  {kind, text, shooter, target, cell, hit, special, ...}
                                (kind is "hit"|"miss"|"sunk"|"cast"; special is only set
                                -- to the caster's country -- when kind is "cast", which
                                may also carry extra special-specific fields, e.g. USA/
                                Italy's "cells"/"hits" or URSS's "revived_cells")
                       reveal {target, cells}
                                (China's surveillance only, sent to the caster alone --
                                the one exception to "state never reveals afloat ship
                                positions"; the ~1s display window is enforced
                                client-side, not by holding data back afterward)
                       prompt {kind: "pakistan", deadline_ms}
                                (sent to every living, unshielded seat other than the
                                caster when Pakistan casts; reply with "respond" before
                                deadline_ms elapses or it's treated as an implicit Accept)
"""

import time
from dataclasses import dataclass

from ..config import PAKISTAN_VOTE_SECONDS
from ..engine.skirmish import Skirmish
from ..models.grid import Grid
from ..models.player import Player

_TICK_SECONDS = 0.01


@dataclass
class Endpoint:
    conn: object  # a connection.Connection or LoopbackConnection
    name: str
    country: str


def serve(endpoints):
    """Run one match to completion over the given seat-ordered endpoints
    (seat index = position in the list; the host is seat 0 via loopback).
    """
    GameServer(endpoints).run()


class GameServer:
    def __init__(self, endpoints):
        self.endpoints = list(endpoints)
        self.seats = [{"name": e.name, "country": e.country} for e in self.endpoints]
        self.game = None

    # --- lifecycle ---------------------------------------------------------

    def run(self):
        for seat, endpoint in enumerate(self.endpoints):
            self._send(seat, {"type": "roster", "seats": self.seats, "you": seat})
            self._send(seat, {"type": "place"})

        players, dropped = self._collect_fleets()
        self.game = Skirmish(players)
        for seat in dropped:
            self.game.eliminate(seat)
        self._broadcast_state()

        self._play()

    def _collect_fleets(self):
        """Wait until every seat has sent its placed fleet. A seat that drops
        during placement becomes an empty (already-eliminated) grid so the rest
        can still start.
        """
        players = [None] * len(self.endpoints)
        dropped = set()
        while any(player is None for player in players):
            for seat, endpoint in enumerate(self.endpoints):
                if players[seat] is not None:
                    continue
                try:
                    message = endpoint.conn.poll()
                except ConnectionError:
                    players[seat] = self._make_player(seat, boats=[])
                    dropped.add(seat)
                    continue
                if message is not None and message.get("type") == "ready":
                    players[seat] = self._make_player(seat, message.get("boats", []))
            time.sleep(_TICK_SECONDS)
        return players, dropped

    def _make_player(self, seat, boats):
        player = Player(self.seats[seat]["name"], country=self.seats[seat]["country"])
        grid = Grid()
        for spec in boats:
            grid.add_boat([tuple(cell) for cell in spec["cells"]], name=spec.get("name"))
        player.grid = grid
        return player

    def _play(self):
        while not self.game.is_over:
            for seat, endpoint in enumerate(self.endpoints):
                try:
                    message = endpoint.conn.poll()
                except ConnectionError:
                    self._handle_drop(seat)
                    break  # seat list/turn may have shifted; restart the sweep
                if message is None or seat != self.game.turn:
                    continue  # only the player on turn may act; ignore stray intents
                msg_type = message.get("type")
                if msg_type == "fire":
                    self._resolve_fire(seat, message)
                elif msg_type == "cast":
                    self._resolve_cast(seat, message)
                if self.game.is_over:
                    break
            time.sleep(_TICK_SECONDS)
        self._broadcast_state()  # final snapshot carries over=True and the winner

    def _resolve_fire(self, seat, message):
        cell = (message["x"], message["y"])
        outcome = self.game.resolve_shot(seat, message["target"], cell)
        if not outcome.valid:
            return  # client already guards against illegal shots; nothing to broadcast
        self._broadcast({"type": "event", **self._event(outcome)})
        self._broadcast_state()

    def _resolve_cast(self, seat, message):
        outcome = self.game.resolve_cast(seat, payload=message.get("payload", {}))
        if not outcome.valid:
            return  # client already guards against illegal/unaffordable casts
        event = self._cast_event(outcome)
        private = event.pop("private", None)  # e.g. China's surveillance -- never goes out on the broadcast
        self._broadcast({"type": "event", **event})
        if private is not None:
            self._send(seat, {"type": "reveal", **private})
        self._broadcast_state()
        if (outcome.effect or {}).get("deferred"):
            self._run_pakistan_vote(seat, outcome.effect["participants"])

    def _run_pakistan_vote(self, shooter, participants):
        """Block until every participant has Accepted/Refused or the clock
        runs out, then apply the outcome. Self-contained on purpose (see the
        Phase 5 plan): this is the one special that needs input from players
        other than the caster, so it can't resolve inside Skirmish.resolve_cast
        like every other handler -- _play()'s normal per-tick dispatch is
        simply paused for the duration, same cooperative poll+sleep style as
        the rest of this file.
        """
        deadline_ms = int(PAKISTAN_VOTE_SECONDS * 1000)
        for seat in participants:
            self._send(seat, {"type": "prompt", "kind": "pakistan", "deadline_ms": deadline_ms})

        responses = {}  # seat -> "accept"/"refuse", insertion-ordered by arrival
        pending = set(participants)
        deadline = time.monotonic() + PAKISTAN_VOTE_SECONDS
        while pending and time.monotonic() < deadline:
            for seat in list(pending):
                try:
                    message = self.endpoints[seat].conn.poll()
                except ConnectionError:
                    self._handle_drop(seat)  # eliminated -- excluded from the outcome below
                    pending.discard(seat)
                    continue
                if message is not None and message.get("type") == "respond" and message.get("choice") in (
                    "accept",
                    "refuse",
                ):
                    responses[seat] = message["choice"]
                    pending.discard(seat)
            time.sleep(_TICK_SECONDS)

        refused = [seat for seat in participants if responses.get(seat) == "refuse"]
        # Anyone who ran out the clock without refusing is an implicit Accept
        # (see the Phase 5 plan) -- appended after explicit accepters, in seat
        # order, as a deterministic tiebreak for simultaneous timeouts.
        accepted_order = [seat for seat in responses if responses[seat] == "accept"]
        accepted_order += [seat for seat in participants if seat not in responses]
        accepted_order = [seat for seat in accepted_order if self.game.alive[seat]]  # drop anyone who disconnected

        self.game.resolve_pakistan_vote(shooter, refused, accepted_order)
        self._broadcast({"type": "event", **self._pakistan_result_event(shooter, refused, accepted_order)})
        self._broadcast_state()

    def _pakistan_result_event(self, shooter, refused, accepted_order):
        shooter_name = self.seats[shooter]["name"]
        ponzi_loser = accepted_order[-1] if accepted_order else None
        clauses = [f"{self.seats[s]['name']} refuse et subit 3 tirs" for s in refused]
        if ponzi_loser is not None:
            clauses.append(f"{self.seats[ponzi_loser]['name']} est le dernier à accepter et perd un navire")
        text = ". ".join(clauses) + "." if clauses else f"Personne n'a mordu à l'offre de {shooter_name}."
        return {
            "kind": "cast",
            "text": text,
            "shooter": shooter,
            "target": None,
            "cell": None,
            "hit": False,
            "special": "Pakistan",
            "refused": refused,
            "accepted": accepted_order,
            "ponzi_loser": ponzi_loser,
        }

    def _handle_drop(self, seat):
        if not self.game.alive[seat]:
            return
        self.game.eliminate(seat)
        self._broadcast(
            {
                "type": "event",
                "kind": "miss",
                "text": f"{self.seats[seat]['name']} a quitté la partie.",
                "shooter": seat,
                "target": seat,
                "cell": None,
                "hit": False,
            }
        )
        self._broadcast_state()

    # --- events / broadcast ------------------------------------------------

    def _event(self, outcome):
        shooter = self.seats[outcome.shooter]["name"]
        target = self.seats[outcome.target]["name"]
        if outcome.eliminated:
            kind, text = "sunk", f"{shooter} a coulé le {outcome.boat_name} de {target} et l'a ÉLIMINÉ !"
        elif outcome.sunk_boat is not None:
            kind, text = "sunk", f"{shooter} a coulé le {outcome.boat_name} de {target} !"
        elif outcome.hit:
            kind, text = "hit", f"{shooter} a touché le {outcome.boat_name} de {target}."
        else:
            kind, text = "miss", f"{shooter} a raté {target}."
        return {
            "kind": kind,
            "text": text,
            "shooter": outcome.shooter,
            "target": outcome.target,
            "cell": [outcome.cell[0], outcome.cell[1]],
            "hit": outcome.hit,
            "boat_name": outcome.boat_name,
        }

    def _cast_event(self, outcome):
        shooter = self.seats[outcome.shooter]["name"]
        event = {
            "kind": "cast",
            "text": f"{shooter} utilise son spécial : {outcome.special}.",
            "shooter": outcome.shooter,
            "target": None,
            "cell": None,
            "hit": False,
            "special": outcome.special,
        }
        event.update(outcome.effect or {})  # e.g. affected cells/hits, target -- special-specific
        return event

    def _broadcast_state(self):
        self._broadcast({"type": "state", **self.game.public_snapshot()})

    def _broadcast(self, message):
        for seat in range(len(self.endpoints)):
            self._send(seat, message)

    def _send(self, seat, message):
        try:
            self.endpoints[seat].conn.send(message)
        except OSError:
            pass  # a dead socket; the poll sweep will register the drop authoritatively
