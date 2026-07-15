"""Country-specific special-cast handlers (Phase 2: USA, Italy, URSS).

Phase 1's generic cast pathway (energy, turn-consumption, unknown-country
rejection) is covered in test_skirmish.py; this file is about each country's
own effect and eligibility rules.
"""

from battleship.config import BOARD_SIZE, KILL_BONUS, PAKISTAN_OFFER_TEXTS, PAKISTAN_REFUSAL_HITS, SPECIAL_COSTS
from battleship.engine.skirmish import Skirmish
from battleship.models.player import Player


def make_players(countries):
    """One player per country, each with a distinct-row 2-cell boat (row r:
    cells (0, r) and (1, r)), mirroring test_skirmish.py's make_players.
    """
    players = []
    for i, country in enumerate(countries):
        player = Player(f"P{i}", country=country)
        player.grid.place(0, i, 2, (1, 0))
        players.append(player)
    return players


def fund(game, seat, amount):
    game.players[seat].energy = amount


# --- USA: 4x4 block, max 2 casts/game -------------------------------------


def test_usa_nuke_hits_every_boat_cell_in_the_block():
    game = Skirmish(make_players(["USA", "China"]))
    fund(game, 0, SPECIAL_COSTS["USA"])

    outcome = game.resolve_cast(0, {"target": 1, "x": 0, "y": 0})

    assert outcome.valid is True
    assert outcome.effect["target"] == 1
    assert sorted(outcome.effect["hits"]) == [[0, 1], [1, 1]]  # P1's whole boat is inside the block
    assert game.players[1].grid.sunk_boats
    assert outcome.over is True  # sinking P1's only boat with just 2 players ends the match


def test_usa_nuke_rejects_a_block_that_would_go_out_of_bounds():
    game = Skirmish(make_players(["USA", "China"]))
    fund(game, 0, SPECIAL_COSTS["USA"])

    outcome = game.resolve_cast(0, {"target": 1, "x": BOARD_SIZE - 2, "y": 0})

    assert outcome.valid is False
    assert outcome.reason == "out of bounds"
    assert game.players[0].energy == SPECIAL_COSTS["USA"]  # rejected -- nothing spent
    assert game.turn == 0  # turn not consumed


def test_usa_nuke_skips_already_shot_cells_instead_of_rejecting():
    game = Skirmish(make_players(["USA", "China"]))
    game.resolve_shot(0, 1, (0, 1))  # pre-shoot one of the boat's two cells (hit -> extra shot)
    fund(game, 0, SPECIAL_COSTS["USA"])

    outcome = game.resolve_cast(0, {"target": 1, "x": 0, "y": 0})

    assert outcome.valid is True
    assert [0, 1] not in outcome.effect["hits"]  # already-shot cell wasn't re-applied
    assert [1, 1] in outcome.effect["hits"]  # the boat's other, still-fresh cell
    assert game.players[1].grid.sunk_boats  # both cells now hit either way


def test_usa_nuke_can_only_be_cast_twice_per_game():
    game = Skirmish(make_players(["USA", "China"]))
    for _ in range(2):
        fund(game, 0, SPECIAL_COSTS["USA"])
        outcome = game.resolve_cast(0, {"target": 1, "x": 5, "y": 5})
        assert outcome.valid is True
        game.turn = 0  # back to seat 0 for the test's sake

    fund(game, 0, SPECIAL_COSTS["USA"])
    outcome = game.resolve_cast(0, {"target": 1, "x": 5, "y": 5})

    assert outcome.valid is False
    assert outcome.reason == "already cast twice this game"


def test_public_snapshot_exposes_the_usa_cast_count():
    game = Skirmish(make_players(["USA", "China"]))
    assert game.public_snapshot()["boards"][0]["usa_casts"] == 0

    fund(game, 0, SPECIAL_COSTS["USA"])
    game.resolve_cast(0, {"target": 1, "x": 5, "y": 5})

    assert game.public_snapshot()["boards"][0]["usa_casts"] == 1


# --- Italy: full row or column ---------------------------------------------


def test_italy_row_hits_every_boat_cell_on_that_row():
    game = Skirmish(make_players(["Italy", "China"]))
    fund(game, 0, SPECIAL_COSTS["Italy"])

    outcome = game.resolve_cast(0, {"target": 1, "axis": "row", "index": 1})

    assert outcome.valid is True
    assert sorted(outcome.effect["hits"]) == [[0, 1], [1, 1]]
    assert game.players[1].grid.sunk_boats


def test_italy_column_hits_only_the_matching_cell():
    game = Skirmish(make_players(["Italy", "China"]))
    fund(game, 0, SPECIAL_COSTS["Italy"])

    outcome = game.resolve_cast(0, {"target": 1, "axis": "col", "index": 0})

    assert outcome.valid is True
    assert outcome.effect["hits"] == [[0, 1]]  # only the x=0 cell of the boat
    assert game.players[1].grid.sunk_boats == []  # just one of its two cells


def test_italy_rejects_an_out_of_bounds_index():
    game = Skirmish(make_players(["Italy", "China"]))
    fund(game, 0, SPECIAL_COSTS["Italy"])

    outcome = game.resolve_cast(0, {"target": 1, "axis": "row", "index": BOARD_SIZE})

    assert outcome.valid is False
    assert outcome.reason == "out of bounds"


# --- URSS: restore a ship sunk since your last turn -----------------------


def test_urss_is_ineligible_with_nothing_sunk():
    game = Skirmish(make_players(["URSS", "China"]))
    fund(game, 0, SPECIAL_COSTS["URSS"])

    outcome = game.resolve_cast(0, {})

    assert outcome.valid is False
    assert outcome.reason == "no sunk ship to restore"


def test_urss_restores_a_ship_sunk_since_its_last_turn():
    players = make_players(["URSS", "China"])
    players[0].grid.add_boat([(5, 5), (5, 6)], name="Reserve")  # a 2nd boat so the 1st sinking isn't fatal
    game = Skirmish(players)

    game.resolve_shot(0, 1, (9, 9))  # seat0 misses -> seat1's turn
    game.resolve_shot(1, 0, (0, 0))  # hit
    game.resolve_shot(1, 0, (1, 0))  # sinks seat0's first boat (not the last one) -> extra
    game.resolve_shot(1, 0, (9, 9))  # miss -> back to seat0
    fund(game, 0, SPECIAL_COSTS["URSS"])

    outcome = game.resolve_cast(0, {})

    assert outcome.valid is True
    assert sorted(outcome.effect["revived_cells"]) == [[0, 0], [1, 0]]
    assert game.players[0].grid.floating_boats  # revived boat is back among them
    assert game.players[0].grid.sunk_boats == []
    assert (0, 0) not in game.shots[0]  # cleared so it can be shot (and sunk) again
    assert game.turn == 1


def test_urss_is_ineligible_once_a_full_turn_has_passed_without_a_new_sink():
    players = make_players(["URSS", "China"])
    players[0].grid.add_boat([(5, 5), (5, 6)], name="Reserve")
    game = Skirmish(players)

    game.resolve_shot(0, 1, (9, 9))  # seat0 -> miss -> seat1
    game.resolve_shot(1, 0, (0, 0))  # hit
    game.resolve_shot(1, 0, (1, 0))  # sinks seat0's first boat -> extra
    game.resolve_shot(1, 0, (9, 9))  # miss -> back to seat0

    game.resolve_shot(0, 1, (8, 9))  # seat0's NEW turn (updates its turn-start marker) -> miss -> seat1
    game.resolve_shot(1, 0, (7, 9))  # seat1 misses, no new sink -> back to seat0
    fund(game, 0, SPECIAL_COSTS["URSS"])

    outcome = game.resolve_cast(0, {})

    assert outcome.valid is False
    assert outcome.reason == "no ship of yours was sunk since your last turn"


# --- Congo: shield + fragile revive, no back-to-back ------------------------


def test_congo_shield_blocks_normal_fire_at_its_owner():
    players = make_players(["Congo", "China", "URSS"])
    game = Skirmish(players)
    fund(game, 0, SPECIAL_COSTS["Congo"])

    outcome = game.resolve_cast(0, {})
    assert outcome.valid is True

    blocked = game.resolve_shot(1, 0, (0, 0))

    assert blocked.valid is False
    assert blocked.reason == "target is shielded"


def test_congo_shield_also_blocks_other_specials_from_targeting_its_owner():
    players = make_players(["Congo", "USA", "URSS"])
    game = Skirmish(players)
    fund(game, 0, SPECIAL_COSTS["Congo"])
    game.resolve_cast(0, {})  # turn -> 1
    fund(game, 1, SPECIAL_COSTS["USA"])

    outcome = game.resolve_cast(1, {"target": 0, "x": 0, "y": 0})

    assert outcome.valid is False
    assert outcome.reason == "target is shielded"


def test_congo_shield_expires_when_its_owner_takes_their_next_turn():
    players = make_players(["Congo", "China", "URSS"])
    game = Skirmish(players)
    fund(game, 0, SPECIAL_COSTS["Congo"])
    game.resolve_cast(0, {})  # turn -> 1
    game.resolve_shot(1, 2, (9, 9))  # miss -> 2
    game.resolve_shot(2, 1, (9, 9))  # miss -> back to seat0
    game.resolve_shot(0, 1, (8, 9))  # seat0's own next turn: shield clears here -> miss -> 1

    outcome = game.resolve_shot(1, 0, (0, 0))  # seat1 can target seat0 again

    assert outcome.valid is True
    assert outcome.hit is True


def test_congo_cannot_be_cast_two_turns_in_a_row():
    players = make_players(["Congo", "China", "URSS"])
    game = Skirmish(players)
    fund(game, 0, SPECIAL_COSTS["Congo"])
    game.resolve_cast(0, {})  # turn -> 1
    game.resolve_shot(1, 2, (9, 9))  # miss -> 2
    game.resolve_shot(2, 1, (9, 9))  # miss -> back to seat0
    fund(game, 0, SPECIAL_COSTS["Congo"])

    outcome = game.resolve_cast(0, {})

    assert outcome.valid is False
    assert outcome.reason == "cannot cast two turns in a row"


def test_congo_can_be_cast_again_after_one_intervening_turn():
    players = make_players(["Congo", "China", "URSS"])
    game = Skirmish(players)
    fund(game, 0, SPECIAL_COSTS["Congo"])
    game.resolve_cast(0, {})  # turn -> 1
    game.resolve_shot(1, 2, (9, 9))  # miss -> 2
    game.resolve_shot(2, 1, (9, 9))  # miss -> back to seat0
    game.resolve_shot(0, 1, (8, 9))  # seat0's own turn: cooldown clears here -> miss -> 1
    game.resolve_shot(1, 2, (8, 9))  # miss -> 2
    game.resolve_shot(2, 1, (7, 9))  # a fresh cell for target1 (not (8,9) again) -> miss -> back to seat0
    fund(game, 0, SPECIAL_COSTS["Congo"])

    outcome = game.resolve_cast(0, {})

    assert outcome.valid is True


def test_congo_revives_a_sunk_ship_fragile():
    # 3 players so there's always a legal (non-shielded) target to fire at
    # while seat0's shield is up -- with only 2, the sole opponent would be
    # shielded and have nothing legal to fire at.
    players = make_players(["Congo", "China", "URSS"])
    players[0].grid.add_boat([(5, 5), (5, 6)], name="Reserve")  # 2nd boat so the 1st sinking isn't fatal
    game = Skirmish(players)
    game.resolve_shot(0, 1, (9, 9))  # seat0 -> seat1, miss -> turn 1
    game.resolve_shot(1, 0, (0, 0))  # seat1 -> seat0, hit -> extra, turn stays 1
    game.resolve_shot(1, 0, (1, 0))  # sinks seat0's first boat (not last) -> extra, turn stays 1
    game.resolve_shot(1, 0, (9, 9))  # miss -> turn 2
    game.resolve_shot(2, 0, (8, 9))  # seat2 -> seat0, miss -> back to seat0's own turn
    fund(game, 0, SPECIAL_COSTS["Congo"])

    outcome = game.resolve_cast(0, {})  # revives + shields -> turn 1

    assert outcome.valid is True
    assert sorted(outcome.effect["revived_cells"]) == [[0, 0], [1, 0]]
    revived = next(b for b in game.players[0].grid.floating_boats if (0, 0) in [c for c, _ in b.cells])
    assert revived.hits_remaining == 1  # fragile, unlike URSS's full restore

    game.resolve_shot(1, 2, (9, 9))  # seat1 can't target shielded seat0 -> fires at seat2 instead, miss -> turn 2
    game.resolve_shot(2, 1, (8, 9))  # seat2 can't target shielded seat0 either -> fires at seat1, miss -> turn 0
    game.resolve_shot(0, 1, (7, 9))  # seat0's own next turn: shield clears here -> miss -> turn 1

    resink = game.resolve_shot(1, 0, (0, 0))  # NOW seat1 can hit seat0's revived boat again

    assert resink.hit is True
    assert resink.sunk_boat is revived


def test_congo_still_grants_the_shield_with_nothing_to_revive():
    players = make_players(["Congo", "China"])
    game = Skirmish(players)
    fund(game, 0, SPECIAL_COSTS["Congo"])

    outcome = game.resolve_cast(0, {})

    assert outcome.valid is True
    assert outcome.effect == {}
    assert game.special_state[0]["congo_shielded"] is True


# --- Brésil: steal a random floating boat ------------------------------------


def test_bresil_steals_a_boat_and_places_it_on_the_thiefs_own_board():
    players = make_players(["Bresil", "China"])
    game = Skirmish(players)
    fund(game, 0, SPECIAL_COSTS["Bresil"])

    outcome = game.resolve_cast(0, {"target": 1})

    assert outcome.valid is True
    assert outcome.effect["target"] == 1
    assert game.players[1].grid.floating_boats == []  # China's only boat is gone
    assert len(game.players[0].grid.floating_boats) == 2  # its own boat plus the stolen one

    own_cells = {(0, 0), (1, 0)}  # seat0's original boat, from make_players
    all_cells = [cell for boat in game.players[0].grid.floating_boats for cell, _ in boat.cells]
    assert len(all_cells) == len(set(all_cells))  # the two boats don't overlap
    stolen_cells = set(all_cells) - own_cells
    assert stolen_cells == {tuple(c) for c in outcome.effect["new_cells"]}


def test_bresil_stealing_the_targets_last_ship_eliminates_them():
    players = make_players(["Bresil", "China", "URSS"])
    game = Skirmish(players)
    fund(game, 0, SPECIAL_COSTS["Bresil"])

    outcome = game.resolve_cast(0, {"target": 1})

    assert outcome.valid is True
    assert outcome.effect["eliminated"] is True
    assert game.alive[1] is False
    assert game.is_over is False  # seat2 is still alive


def test_bresil_rejects_targeting_a_shielded_player():
    players = make_players(["Congo", "Bresil", "URSS"])
    game = Skirmish(players)
    fund(game, 0, SPECIAL_COSTS["Congo"])
    game.resolve_cast(0, {})  # seat0 shields itself -> turn to seat1
    fund(game, 1, SPECIAL_COSTS["Bresil"])

    outcome = game.resolve_cast(1, {"target": 0})

    assert outcome.valid is False
    assert outcome.reason == "target is shielded"


# --- China: counterfeit decoy, or peek at half a board ----------------------


def test_china_rejects_an_unknown_mode():
    game = Skirmish(make_players(["China", "USA"]))
    fund(game, 0, SPECIAL_COSTS["China"])

    outcome = game.resolve_cast(0, {})

    assert outcome.valid is False
    assert outcome.reason == "unknown mode"


def test_china_counterfeit_adds_a_fragile_decoy_to_its_own_board():
    game = Skirmish(make_players(["China", "USA"]))
    fund(game, 0, SPECIAL_COSTS["China"])
    original_cells = {cell for cell, _ in game.players[0].grid.floating_boats[0].cells}

    outcome = game.resolve_cast(0, {"mode": "counterfeit"})

    assert outcome.valid is True
    assert outcome.effect["mode"] == "counterfeit"
    assert outcome.effect["placed"] is True
    assert len(outcome.effect["cells"]) == 2  # same size as the boat it duplicates
    assert len(game.players[0].grid.floating_boats) == 2  # real boat + decoy

    decoy = next(b for b in game.players[0].grid.floating_boats if {c for c, _ in b.cells} != original_cells)
    assert decoy.hits_remaining == 1  # fragile: a single hit sinks the fake
    decoy_cells = {cell for cell, _ in decoy.cells}
    assert decoy_cells.isdisjoint(original_cells)  # doesn't overlap the real boat
    assert {tuple(c) for c in outcome.effect["cells"]} == decoy_cells


def test_china_counterfeit_decoy_is_shootable_even_over_previously_missed_water():
    # Mark almost the whole board as already-shot water so the random
    # placement is forced onto a previously-missed cell -- without the fix,
    # such a cell stays permanently rejected as "already shot there", making
    # the decoy (and, if it's all that's left afloat, China itself) unkillable.
    game = Skirmish(make_players(["China", "USA"]))
    boat_cells = {cell for cell, _ in game.players[0].grid.floating_boats[0].cells}
    for x in range(BOARD_SIZE):
        for y in range(BOARD_SIZE):
            if (x, y) not in boat_cells:
                game.shots[0][(x, y)] = False
    fund(game, 0, SPECIAL_COSTS["China"])

    outcome = game.resolve_cast(0, {"mode": "counterfeit"})

    assert outcome.effect["placed"] is True
    for cell in outcome.effect["cells"]:
        assert tuple(cell) not in game.shots[0]  # cleared -- an opponent can shoot it


def test_china_surveillance_reveals_boats_only_in_the_chosen_half():
    players = make_players(["China", "USA"])
    game = Skirmish(players)
    fund(game, 0, SPECIAL_COSTS["China"])

    outcome = game.resolve_cast(0, {"mode": "surveillance", "target": 1, "axis": "row", "half": "low"})

    assert outcome.valid is True
    assert outcome.effect["target"] == 1
    # USA's boat from make_players sits on row 1 (cells (0,1)/(1,1)) -- inside rows 0-4.
    assert sorted(outcome.effect["private"]["cells"]) == [[0, 1], [1, 1]]


def test_china_surveillance_reveals_nothing_from_the_other_half():
    players = make_players(["China", "USA"])
    game = Skirmish(players)
    fund(game, 0, SPECIAL_COSTS["China"])

    outcome = game.resolve_cast(0, {"mode": "surveillance", "target": 1, "axis": "row", "half": "high"})

    assert outcome.valid is True
    assert outcome.effect["private"]["cells"] == []  # USA's only boat is on row 1, not rows 5-9


def test_china_surveillance_rejects_missing_axis_or_half():
    game = Skirmish(make_players(["China", "USA"]))
    fund(game, 0, SPECIAL_COSTS["China"])

    outcome = game.resolve_cast(0, {"mode": "surveillance", "target": 1})

    assert outcome.valid is False
    assert outcome.reason == "missing axis/half"


def test_china_surveillance_rejects_targeting_a_shielded_player():
    players = make_players(["Congo", "China", "URSS"])
    game = Skirmish(players)
    fund(game, 0, SPECIAL_COSTS["Congo"])
    game.resolve_cast(0, {})  # seat0 shields itself -> turn to seat1
    fund(game, 1, SPECIAL_COSTS["China"])

    outcome = game.resolve_cast(1, {"mode": "surveillance", "target": 0, "axis": "row", "half": "low"})

    assert outcome.valid is False
    assert outcome.reason == "target is shielded"


# --- Pakistan: broadcast Ponzi vote, resolved after the fact ----------------


def test_pakistan_is_ineligible_with_no_valid_participant():
    players = make_players(["Congo", "Pakistan"])
    game = Skirmish(players)
    fund(game, 0, SPECIAL_COSTS["Congo"])
    game.resolve_cast(0, {})  # seat0 shields itself -> turn to seat1
    fund(game, 1, SPECIAL_COSTS["Pakistan"])

    outcome = game.resolve_cast(1, {})

    assert outcome.valid is False
    assert outcome.reason == "no valid opponent to prank"


def test_pakistan_cast_defers_the_turn_advance_until_the_vote_resolves():
    players = make_players(["Pakistan", "China", "URSS"])
    game = Skirmish(players)
    fund(game, 0, SPECIAL_COSTS["Pakistan"])

    outcome = game.resolve_cast(0, {})

    assert outcome.valid is True
    assert outcome.effect["deferred"] is True
    assert sorted(outcome.effect["participants"]) == [1, 2]
    assert game.turn == 0  # not advanced yet -- resolve_pakistan_vote does that once the vote is in
    assert game.action_count == 0  # likewise not yet incremented


def test_pakistan_cast_text_is_one_of_the_configured_offers_formatted_with_the_shooters_name():
    players = make_players(["Pakistan", "China", "URSS"])
    players[0].name = "Zahra"
    game = Skirmish(players)
    fund(game, 0, SPECIAL_COSTS["Pakistan"])

    outcome = game.resolve_cast(0, {})

    expected_texts = {template.format(shooter="Zahra") for template in PAKISTAN_OFFER_TEXTS}
    assert outcome.effect["text"] in expected_texts


def test_pakistan_participants_exclude_a_shielded_seat():
    players = make_players(["Congo", "Pakistan", "URSS"])
    game = Skirmish(players)
    fund(game, 0, SPECIAL_COSTS["Congo"])
    game.resolve_cast(0, {})  # seat0 shields itself -> turn to seat1
    fund(game, 1, SPECIAL_COSTS["Pakistan"])

    outcome = game.resolve_cast(1, {})

    assert outcome.valid is True
    assert outcome.effect["participants"] == [2]  # seat0 excluded -- shielded


def test_resolve_pakistan_vote_hits_each_refuser_three_times_and_advances_the_turn(monkeypatch):
    monkeypatch.setattr("battleship.engine.specials.random.shuffle", lambda seq: None)
    players = make_players(["Pakistan", "China", "URSS"])
    game = Skirmish(players)
    fund(game, 0, SPECIAL_COSTS["Pakistan"])
    game.resolve_cast(0, {})

    over = game.resolve_pakistan_vote(0, refused=[1, 2], accepted_order=[])

    assert over is False
    assert len(game.shots[1]) == PAKISTAN_REFUSAL_HITS
    assert len(game.shots[2]) == PAKISTAN_REFUSAL_HITS
    assert game.turn == 1  # advanced off seat0 now that the vote has resolved
    assert game.action_count == 1


def test_resolve_pakistan_vote_sinks_the_last_accepters_ship_only():
    players = make_players(["Pakistan", "China", "URSS"])
    game = Skirmish(players)
    fund(game, 0, SPECIAL_COSTS["Pakistan"])
    game.resolve_cast(0, {})

    game.resolve_pakistan_vote(0, refused=[], accepted_order=[1, 2])  # seat2 is last -> pays the Ponzi price

    assert game.players[2].grid.floating_boats == []  # its only boat, gone
    assert game.alive[2] is False  # that was its last ship
    assert game.players[1].grid.floating_boats  # accepted too, but wasn't last -- untouched


def test_resolve_pakistan_vote_credits_the_caster_for_the_ponzi_kill():
    players = make_players(["Pakistan", "China", "URSS"])
    game = Skirmish(players)
    fund(game, 0, SPECIAL_COSTS["Pakistan"])
    game.resolve_cast(0, {})

    game.resolve_pakistan_vote(0, refused=[], accepted_order=[2])

    assert game.players[0].score == KILL_BONUS  # sinking seat2's last ship eliminated them


def test_resolve_pakistan_vote_is_a_no_op_ponzi_when_everyone_refuses():
    players = make_players(["Pakistan", "China", "URSS"])
    game = Skirmish(players)
    fund(game, 0, SPECIAL_COSTS["Pakistan"])
    game.resolve_cast(0, {})

    game.resolve_pakistan_vote(0, refused=[1, 2], accepted_order=[])

    assert game.players[0].score == 0  # no ponzi loser -- nothing to credit
