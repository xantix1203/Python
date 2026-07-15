"""End-to-end test of the authoritative host over in-process loopback links,
with no pygame and no real sockets: scripted clients play a tiny 2-player match
to completion and we assert the broadcast protocol behaves.
"""

import threading
import time

from battleship.config import SPECIAL_COSTS
from battleship.network.connection import loopback_pair
from battleship.network.server import Endpoint, GameServer, serve


def _wait_for(conn, msg_type, timeout=2):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        message = conn.poll()
        if message is not None and message.get("type") == msg_type:
            return message
        time.sleep(0.005)
    raise AssertionError(f"timed out waiting for a {msg_type!r} message")


def _drain_latest_state(conn, timeout=2):
    """Return the newest `state` message currently queued, waiting for at least
    one. Lets a test skip past intermediate snapshots to the settled state.
    """
    latest = _wait_for(conn, "state", timeout)
    while True:
        message = conn.poll()
        if message is None:
            return latest
        if message.get("type") == "state":
            latest = message


def test_two_player_match_plays_to_a_win_over_loopback():
    server_end0, client0 = loopback_pair()
    server_end1, client1 = loopback_pair()
    endpoints = [Endpoint(server_end0, "Host", "USA"), Endpoint(server_end1, "Joiner", "China")]

    thread = threading.Thread(target=serve, args=(endpoints,), daemon=True)
    thread.start()

    # Both clients receive the roster and the placement cue, then submit fleets.
    roster0 = _wait_for(client0, "roster")
    assert roster0["you"] == 0
    assert [seat["name"] for seat in roster0["seats"]] == ["Host", "Joiner"]
    _wait_for(client1, "roster")
    _wait_for(client0, "place")
    _wait_for(client1, "place")

    client0.send({"type": "ready", "boats": [{"cells": [[0, 0], [1, 0]], "name": "A"}]})
    client1.send({"type": "ready", "boats": [{"cells": [[0, 1], [1, 1]], "name": "B"}]})

    # Game starts; it's seat 0's turn. Sink seat 1's only boat to win.
    state = _drain_latest_state(client0)
    assert state["turn"] == 0
    assert state["over"] is False

    client0.send({"type": "fire", "target": 1, "x": 0, "y": 1})  # hit -> extra shot
    state = _drain_latest_state(client0)
    assert state["extra"] is True
    assert state["turn"] == 0

    client0.send({"type": "fire", "target": 1, "x": 1, "y": 1})  # sink -> eliminate -> win
    final = _drain_latest_state(client0)
    assert final["over"] is True
    assert final["winner"] == 0
    assert final["boards"][0]["score"] == 3  # kill bonus
    assert final["boards"][1]["alive"] is False

    # The same authoritative final state reached the other client too.
    final1 = _drain_latest_state(client1)
    assert final1["over"] is True
    assert final1["winner"] == 0

    thread.join(timeout=2)
    assert not thread.is_alive()


def test_hit_event_carries_the_boat_name_even_when_not_sunk():
    server_end0, client0 = loopback_pair()
    server_end1, client1 = loopback_pair()
    endpoints = [Endpoint(server_end0, "Host", "USA"), Endpoint(server_end1, "Joiner", "China")]
    threading.Thread(target=serve, args=(endpoints,), daemon=True).start()

    for client in (client0, client1):
        _wait_for(client, "roster")
        _wait_for(client, "place")
    client0.send({"type": "ready", "boats": [{"cells": [[0, 0], [1, 0]], "name": "A"}]})
    client1.send({"type": "ready", "boats": [{"cells": [[0, 1], [1, 1], [2, 1]], "name": "Le Titanic"}]})

    client0.send({"type": "fire", "target": 1, "x": 0, "y": 1})  # hits one of Le Titanic's three cells

    event = _wait_for(client0, "event")
    assert event["kind"] == "hit"
    assert event["boat_name"] == "Le Titanic"
    assert "Le Titanic" in event["text"]


def test_out_of_turn_fire_is_ignored():
    server_end0, client0 = loopback_pair()
    server_end1, client1 = loopback_pair()
    endpoints = [Endpoint(server_end0, "Host", "USA"), Endpoint(server_end1, "Joiner", "China")]
    threading.Thread(target=serve, args=(endpoints,), daemon=True).start()

    for client in (client0, client1):
        _wait_for(client, "roster")
        _wait_for(client, "place")
    client0.send({"type": "ready", "boats": [{"cells": [[0, 0], [1, 0]], "name": "A"}]})
    client1.send({"type": "ready", "boats": [{"cells": [[0, 1], [1, 1]], "name": "B"}]})

    initial = _drain_latest_state(client1)
    assert initial["turn"] == 0

    # Seat 1 fires though it is seat 0's turn: must be ignored (no state change).
    client1.send({"type": "fire", "target": 0, "x": 0, "y": 0})
    time.sleep(0.1)
    later = client1.poll()
    while later is not None and later.get("type") != "state":
        later = client1.poll()
    assert later is None  # no new snapshot -> the illegal shot changed nothing
    assert initial["boards"][0]["ships_left"] == 1  # seat 0's boat untouched


def test_cast_without_enough_energy_is_ignored():
    server_end0, client0 = loopback_pair()
    server_end1, client1 = loopback_pair()
    endpoints = [Endpoint(server_end0, "Host", "USA"), Endpoint(server_end1, "Joiner", "China")]
    threading.Thread(target=serve, args=(endpoints,), daemon=True).start()

    for client in (client0, client1):
        _wait_for(client, "roster")
        _wait_for(client, "place")
    client0.send({"type": "ready", "boats": [{"cells": [[0, 0], [1, 0]], "name": "A"}]})
    client1.send({"type": "ready", "boats": [{"cells": [[0, 1], [1, 1]], "name": "B"}]})

    initial = _drain_latest_state(client0)
    assert initial["boards"][0]["energy"] == 0

    # USA costs 8; only the +1 passive gain is available this turn -- reject.
    client0.send({"type": "cast", "payload": {}})
    time.sleep(0.1)
    later = client0.poll()
    while later is not None and later.get("type") != "state":
        later = client0.poll()
    assert later is None  # no new snapshot -> the unaffordable cast changed nothing


def test_cast_deducts_energy_plays_and_passes_the_turn():
    server_end0, client0 = loopback_pair()
    server_end1, client1 = loopback_pair()
    endpoints = [Endpoint(server_end0, "Host", "Congo"), Endpoint(server_end1, "Joiner", "China")]
    threading.Thread(target=serve, args=(endpoints,), daemon=True).start()

    for client in (client0, client1):
        _wait_for(client, "roster")
        _wait_for(client, "place")
    client0.send({"type": "ready", "boats": [{"cells": [[0, 0], [1, 0]], "name": "A"}]})
    client1.send({"type": "ready", "boats": [{"cells": [[0, 1], [1, 1]], "name": "B"}]})

    # Trade misses at empty water so the host (Congo, cost 4) banks 3 energy
    # from the once-per-own-turn passive gain; the cast's own turn supplies
    # the 4th point atomically. Each round must land on a fresh cell -- both
    # boards' boats sit on rows 0/1, so column 9 downward is safe water.
    for i in range(3):
        client0.send({"type": "fire", "target": 1, "x": 9, "y": 9 - i})
        client1.send({"type": "fire", "target": 0, "x": 9, "y": 9 - i})
        state = _drain_latest_state(client0)
    assert state["boards"][0]["energy"] == 3
    assert state["turn"] == 0

    client0.send({"type": "cast", "payload": {}})

    event = _wait_for(client0, "event")
    assert event["kind"] == "cast"
    assert event["special"] == "Congo"
    assert event["shooter"] == 0

    state = _drain_latest_state(client0)
    assert state["boards"][0]["energy"] == 0  # 3 + 1 (this turn) - 4 (cost)
    assert state["turn"] == 1  # cast never grants a bonus shot


def test_italy_cast_hits_a_whole_row_and_can_end_the_match():
    server_end0, client0 = loopback_pair()
    server_end1, client1 = loopback_pair()
    endpoints = [Endpoint(server_end0, "Host", "Italy"), Endpoint(server_end1, "Joiner", "China")]
    threading.Thread(target=serve, args=(endpoints,), daemon=True).start()

    for client in (client0, client1):
        _wait_for(client, "roster")
        _wait_for(client, "place")
    client0.send({"type": "ready", "boats": [{"cells": [[0, 0], [1, 0]], "name": "A"}]})
    client1.send({"type": "ready", "boats": [{"cells": [[0, 1], [1, 1]], "name": "B"}]})

    # Italy costs 6; bank 5 from misses, the cast's own turn supplies the 6th.
    for i in range(5):
        client0.send({"type": "fire", "target": 1, "x": 9, "y": 9 - i})
        client1.send({"type": "fire", "target": 0, "x": 9, "y": 9 - i})
        state = _drain_latest_state(client0)
    assert state["boards"][0]["energy"] == 5

    client0.send({"type": "cast", "payload": {"target": 1, "axis": "row", "index": 1}})

    event = _wait_for(client0, "event")
    assert event["kind"] == "cast"
    assert event["special"] == "Italy"
    assert sorted(event["hits"]) == [[0, 1], [1, 1]]  # both cells of Joiner's only boat

    final = _drain_latest_state(client0)
    assert final["over"] is True  # sinking their only boat eliminates Joiner -> last one standing
    assert final["winner"] == 0
    assert final["boards"][1]["alive"] is False


def test_china_counterfeit_cast_broadcasts_the_decoy_publicly():
    server_end0, client0 = loopback_pair()
    server_end1, client1 = loopback_pair()
    endpoints = [Endpoint(server_end0, "Host", "China"), Endpoint(server_end1, "Joiner", "USA")]
    threading.Thread(target=serve, args=(endpoints,), daemon=True).start()

    for client in (client0, client1):
        _wait_for(client, "roster")
        _wait_for(client, "place")
    client0.send({"type": "ready", "boats": [{"cells": [[0, 0], [1, 0]], "name": "A"}]})
    client1.send({"type": "ready", "boats": [{"cells": [[0, 1], [1, 1]], "name": "B"}]})

    # China costs 5; bank 4 from misses, the cast's own turn supplies the 5th.
    for i in range(4):
        client0.send({"type": "fire", "target": 1, "x": 9, "y": 9 - i})
        client1.send({"type": "fire", "target": 0, "x": 9, "y": 9 - i})
        state = _drain_latest_state(client0)
    assert state["boards"][0]["energy"] == 4

    client0.send({"type": "cast", "payload": {"mode": "counterfeit"}})

    event = _wait_for(client0, "event")
    assert event["kind"] == "cast"
    assert event["special"] == "China"
    assert event["placed"] is True
    assert len(event["cells"]) == 2  # broadcast publicly -- unlike surveillance, this is not sensitive
    assert "private" not in event

    state = _drain_latest_state(client0)
    assert state["turn"] == 1  # cast never grants a bonus shot


def test_china_surveillance_cast_sends_the_reveal_only_to_the_caster():
    server_end0, client0 = loopback_pair()
    server_end1, client1 = loopback_pair()
    endpoints = [Endpoint(server_end0, "Host", "China"), Endpoint(server_end1, "Joiner", "USA")]
    threading.Thread(target=serve, args=(endpoints,), daemon=True).start()

    for client in (client0, client1):
        _wait_for(client, "roster")
        _wait_for(client, "place")
    client0.send({"type": "ready", "boats": [{"cells": [[0, 0], [1, 0]], "name": "A"}]})
    client1.send({"type": "ready", "boats": [{"cells": [[0, 1], [1, 1]], "name": "B"}]})

    for i in range(4):
        client0.send({"type": "fire", "target": 1, "x": 9, "y": 9 - i})
        client1.send({"type": "fire", "target": 0, "x": 9, "y": 9 - i})
        state = _drain_latest_state(client0)
    assert state["boards"][0]["energy"] == 4

    client0.send({"type": "cast", "payload": {"mode": "surveillance", "target": 1, "axis": "row", "half": "low"}})

    event = _wait_for(client0, "event")
    assert event["kind"] == "cast"
    assert "cells" not in event  # the revealed positions never go out on the public broadcast
    reveal = _wait_for(client0, "reveal")
    assert reveal["target"] == 1
    assert sorted(reveal["cells"]) == [[0, 1], [1, 1]]  # Joiner's whole boat sits on row 1

    # The other client never receives a "reveal" -- only the caster does.
    time.sleep(0.1)
    later = client1.poll()
    while later is not None:
        assert later.get("type") != "reveal"
        later = client1.poll()


def test_pakistan_vote_resolves_from_explicit_responses_and_advances_the_turn():
    server_end0, client0 = loopback_pair()
    server_end1, client1 = loopback_pair()
    server_end2, client2 = loopback_pair()
    endpoints = [
        Endpoint(server_end0, "Host", "Pakistan"),
        Endpoint(server_end1, "P1", "China"),
        Endpoint(server_end2, "P2", "URSS"),
    ]
    server = GameServer(endpoints)
    threading.Thread(target=server.run, daemon=True).start()

    for client in (client0, client1, client2):
        _wait_for(client, "roster")
        _wait_for(client, "place")
    client0.send({"type": "ready", "boats": [{"cells": [[0, 0], [1, 0]], "name": "A"}]})
    client1.send({"type": "ready", "boats": [{"cells": [[0, 1], [1, 1]], "name": "B"}]})
    client2.send({"type": "ready", "boats": [{"cells": [[0, 2], [1, 2]], "name": "C"}]})
    _drain_latest_state(client0)  # match has started -- server.game now exists

    server.game.players[0].energy = SPECIAL_COSTS["Pakistan"] - 1  # the cast's own turn supplies the last point
    client0.send({"type": "cast", "payload": {}})

    announce = _wait_for(client0, "event")
    assert announce["special"] == "Pakistan"

    prompt1 = _wait_for(client1, "prompt")
    assert prompt1["kind"] == "pakistan"
    assert "deadline_ms" in prompt1
    _wait_for(client2, "prompt")

    client1.send({"type": "respond", "choice": "refuse"})
    client2.send({"type": "respond", "choice": "accept"})

    result = _wait_for(client0, "event")
    assert result["special"] == "Pakistan"
    assert result["refused"] == [1]
    assert result["accepted"] == [2]
    assert result["ponzi_loser"] == 2

    final = _drain_latest_state(client0)
    assert final["turn"] == 1  # advanced off seat0 now that the vote has resolved
    assert len(final["boards"][1]["shots"]) == 3  # P1's "opportunity lost" hits
    assert final["boards"][2]["alive"] is False  # P2's only ship was the Ponzi loss

    # The caster itself is never sent a vote prompt.
    stray = client0.poll()
    while stray is not None:
        assert stray.get("type") != "prompt"
        stray = client0.poll()


def test_pakistan_vote_timeout_counts_as_an_implicit_accept(monkeypatch):
    monkeypatch.setattr("battleship.network.server.PAKISTAN_VOTE_SECONDS", 0.05)
    server_end0, client0 = loopback_pair()
    server_end1, client1 = loopback_pair()
    endpoints = [Endpoint(server_end0, "Host", "Pakistan"), Endpoint(server_end1, "Joiner", "China")]
    server = GameServer(endpoints)
    threading.Thread(target=server.run, daemon=True).start()

    for client in (client0, client1):
        _wait_for(client, "roster")
        _wait_for(client, "place")
    client0.send({"type": "ready", "boats": [{"cells": [[0, 0], [1, 0]], "name": "A"}]})
    client1.send({"type": "ready", "boats": [{"cells": [[0, 1], [1, 1]], "name": "B"}]})
    _drain_latest_state(client0)

    server.game.players[0].energy = SPECIAL_COSTS["Pakistan"]
    client0.send({"type": "cast", "payload": {}})

    _wait_for(client0, "event")  # the initial announcement
    _wait_for(client1, "prompt")
    # Joiner never responds -- the vote times out and treats that as an Accept.

    result = _wait_for(client0, "event", timeout=3)
    assert result["refused"] == []
    assert result["accepted"] == [1]
    assert result["ponzi_loser"] == 1  # the only participant -- times out, still "loses" the Ponzi

    final = _drain_latest_state(client0)
    assert final["over"] is True  # 2-player game -- Joiner's only ship was the Ponzi loss
    assert final["winner"] == 0


def test_bresil_cast_steals_the_targets_only_boat():
    server_end0, client0 = loopback_pair()
    server_end1, client1 = loopback_pair()
    endpoints = [Endpoint(server_end0, "Host", "Bresil"), Endpoint(server_end1, "Joiner", "China")]
    threading.Thread(target=serve, args=(endpoints,), daemon=True).start()

    for client in (client0, client1):
        _wait_for(client, "roster")
        _wait_for(client, "place")
    client0.send({"type": "ready", "boats": [{"cells": [[0, 0], [1, 0]], "name": "A"}]})
    client1.send({"type": "ready", "boats": [{"cells": [[0, 1], [1, 1]], "name": "B"}]})

    # Brésil costs 7; bank 6 from misses, the cast's own turn supplies the 7th.
    for i in range(6):
        client0.send({"type": "fire", "target": 1, "x": 9, "y": 9 - i})
        client1.send({"type": "fire", "target": 0, "x": 9, "y": 9 - i})
        state = _drain_latest_state(client0)
    assert state["boards"][0]["energy"] == 6

    client0.send({"type": "cast", "payload": {"target": 1}})

    event = _wait_for(client0, "event")
    assert event["kind"] == "cast"
    assert event["special"] == "Bresil"
    assert event["target"] == 1
    assert sorted(event["stolen_cells"]) == [[0, 1], [1, 1]]  # Joiner's only boat
    assert len(event["new_cells"]) == 2

    final = _drain_latest_state(client0)
    assert final["boards"][1]["alive"] is False  # lost their only ship, with nobody else left standing
    assert final["over"] is True
