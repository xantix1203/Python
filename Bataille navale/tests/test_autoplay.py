"""A full 3-player match played to completion by scripted headless clients over
in-process loopback links. Exercises the server + Skirmish + protocol through
real multi-turn play, extra shots and eliminations -- no pygame, no sockets.
"""

import threading
import time

from battleship.network.connection import loopback_pair
from battleship.network.server import Endpoint, serve


def _auto_client(conn, me, results):
    """Place a two-cell fleet on row 0, then on every turn fire the lowest
    un-shot cell at the first living opponent until the match ends.
    """
    boats = [{"cells": [[2 * me, 0], [2 * me + 1, 0]], "name": "torpilleur"}]
    all_cells = [(x, y) for y in range(10) for x in range(10)]

    while True:
        message = conn.poll()
        if message is None:
            time.sleep(0.002)
            continue
        kind = message.get("type")
        if kind == "place":
            conn.send({"type": "ready", "boats": boats})
        elif kind == "state":
            if message["over"]:
                results[me] = message
                return
            if message["turn"] != me:
                continue
            target = next(
                (s for s, b in enumerate(message["boards"]) if s != me and b["alive"]), None
            )
            if target is None:
                continue
            shot = {(x, y) for x, y, _ in message["boards"][target]["shots"]}
            cell = next((c for c in all_cells if c not in shot), None)
            if cell is not None:
                conn.send({"type": "fire", "target": target, "x": cell[0], "y": cell[1]})


def test_three_player_match_auto_plays_to_a_single_winner():
    ends = [loopback_pair() for _ in range(3)]
    endpoints = [Endpoint(server_end, f"P{i}", "USA") for i, (server_end, _client) in enumerate(ends)]

    server_thread = threading.Thread(target=serve, args=(endpoints,), daemon=True)
    server_thread.start()

    results = {}
    client_threads = [
        threading.Thread(target=_auto_client, args=(client_end, i, results), daemon=True)
        for i, (_server, client_end) in enumerate(ends)
    ]
    for thread in client_threads:
        thread.start()

    server_thread.join(timeout=15)
    assert not server_thread.is_alive(), "the match did not finish in time"
    for thread in client_threads:
        thread.join(timeout=5)

    # Every client observed the same authoritative ending: one winner, and only
    # that winner still standing.
    assert len(results) == 3
    finals = list(results.values())
    winner = finals[0]["winner"]
    assert winner is not None
    assert all(state["winner"] == winner for state in finals)
    alive = [s for s, board in enumerate(finals[0]["boards"]) if board["alive"]]
    assert alive == [winner]
