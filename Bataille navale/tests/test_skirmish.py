from battleship.engine.skirmish import Skirmish
from battleship.models.player import Player


def make_players(n, place=True):
    """n players each holding a single 2-cell boat at a distinct row, so every
    board can be sunk with two known shots. Row r's boat occupies (0, r), (1, r).
    """
    players = []
    for i in range(n):
        player = Player(f"P{i}")
        if place:
            player.grid.place(0, i, 2, (1, 0))  # (0, i) and (1, i)
        players.append(player)
    return players


def sink_board(game, shooter, target):
    """Fire both cells of target's single boat. Returns the sinking Outcome."""
    game.resolve_shot(shooter, target, (0, target))
    return game.resolve_shot(shooter, target, (1, target))


def test_miss_passes_the_turn_to_the_next_seat():
    game = Skirmish(make_players(3))

    outcome = game.resolve_shot(0, 1, (9, 9))  # empty water on P1's board

    assert outcome.valid is True
    assert outcome.hit is False
    assert outcome.extra is False
    assert game.turn == 1


def test_hit_grants_an_extra_shot_and_keeps_the_turn():
    game = Skirmish(make_players(3))

    outcome = game.resolve_shot(0, 1, (0, 1))  # a cell of P1's boat

    assert outcome.hit is True
    assert outcome.extra is True
    assert game.turn == 0  # still the shooter's turn


def test_a_hit_reports_the_boat_name_even_when_not_sunk():
    game = Skirmish(make_players(3))

    outcome = game.resolve_shot(0, 1, (0, 1))  # one of the boat's two cells -- hit, not sunk

    assert outcome.hit is True
    assert outcome.sunk_boat is None
    assert outcome.boat_name == "torpilleur"  # make_players' default 2-cell boat type


def test_a_miss_reports_no_boat_name():
    game = Skirmish(make_players(3))

    outcome = game.resolve_shot(0, 1, (9, 9))  # empty water

    assert outcome.hit is False
    assert outcome.boat_name is None


def test_extra_shot_may_target_a_different_player():
    game = Skirmish(make_players(3))
    game.resolve_shot(0, 1, (0, 1))  # hit P1 -> extra shot

    outcome = game.resolve_shot(0, 2, (0, 2))  # now shoot P2 instead

    assert outcome.valid is True
    assert outcome.hit is True


def test_shot_on_an_already_shot_cell_is_rejected_without_consuming_turn():
    game = Skirmish(make_players(3))
    first = game.resolve_shot(0, 1, (0, 1))  # HIT -> extra shot, turn stays with seat 0
    assert first.valid is True and first.hit is True

    outcome = game.resolve_shot(0, 1, (0, 1))  # exact repeat of a resolved cell

    assert outcome.valid is False
    assert outcome.reason == "already shot there"
    assert game.turn == 0  # turn not consumed by the rejected repeat


def test_cannot_shoot_when_it_is_not_your_turn():
    game = Skirmish(make_players(3))  # seat 0 to move

    outcome = game.resolve_shot(1, 0, (0, 0))

    assert outcome.valid is False
    assert outcome.reason == "not your turn"


def test_cannot_target_yourself():
    game = Skirmish(make_players(3))

    outcome = game.resolve_shot(0, 0, (0, 0))

    assert outcome.valid is False
    assert outcome.reason == "cannot target yourself"


def test_sinking_a_non_last_ship_scores_sink_points():
    players = make_players(2, place=False)
    players[1].grid.place(0, 1, 2, (1, 0))  # row 1, so sink_board's (0,1)/(1,1) hit it
    players[1].grid.place(0, 5, 3, (1, 0))  # a second ship so the first isn't the last
    game = Skirmish(players, sink_points=1, kill_bonus=3)

    outcome = sink_board(game, 0, 1)

    assert outcome.sunk_boat is not None
    assert outcome.boat_name == "torpilleur"
    assert outcome.eliminated is False
    assert players[0].score == 1  # sink points, not the kill bonus


def test_killing_blow_scores_kill_bonus_and_eliminates_the_target():
    game = Skirmish(make_players(3), sink_points=1, kill_bonus=3)

    outcome = sink_board(game, 0, 1)  # P1 has a single ship -> sinking it kills P1

    assert outcome.eliminated is True
    assert game.alive[1] is False
    assert game.players[0].score == 3  # kill bonus, not sink points


def test_turn_order_skips_eliminated_players_and_wraps():
    game = Skirmish(make_players(3), sink_points=1, kill_bonus=3)
    sink_board(game, 0, 1)  # eliminate seat 1; kill keeps the turn (a hit)? no -> see below

    # The sinking shot is a hit, so seat 0 keeps the turn. Miss to pass it on.
    game.resolve_shot(0, 2, (9, 9))

    assert game.turn == 2  # seat 1 is dead and skipped, so it lands on seat 2


def test_last_player_standing_wins():
    game = Skirmish(make_players(2), sink_points=1, kill_bonus=3)

    sink_board(game, 0, 1)  # eliminate the only opponent

    assert game.is_over is True
    assert game.winner == 0


def test_reaching_win_score_ends_the_game_with_ships_still_afloat():
    # Three boards for seat 0 to farm; win at 2 points via two non-last sinks.
    players = make_players(3, place=False)
    for i in (1, 2):
        players[i].grid.place(0, i, 2, (1, 0))  # row i, sinkable via sink_board
        players[i].grid.place(0, 5, 2, (1, 0))  # keep each alive after one sink
    game = Skirmish(players, win_score=2, sink_points=1, kill_bonus=3)

    sink_board(game, 0, 1)  # +1, P1 still alive
    assert game.is_over is False
    sink_board(game, 0, 2)  # +1 -> reaches win_score=2

    assert game.is_over is True
    assert game.winner == 0
    assert game.players[0].score == 2
    assert game.living_seats() == [0, 1, 2]  # nobody eliminated; the race ended it


def test_win_is_checked_before_the_extra_shot_is_granted():
    game = Skirmish(make_players(2), sink_points=1, kill_bonus=3)

    outcome = sink_board(game, 0, 1)  # kills last opponent -> game over

    assert outcome.over is True
    assert outcome.extra is False  # no bonus shot in an already-decided game


def test_eliminated_player_keeps_its_score_and_is_skipped():
    players = make_players(3, place=False)
    players[0].grid.place(0, 0, 2, (1, 0))
    players[1].grid.place(0, 1, 2, (1, 0))
    players[2].grid.place(0, 2, 2, (1, 0))
    game = Skirmish(players, win_score=99, sink_points=1, kill_bonus=3)

    # seat 1 scores a point, then gets knocked out by a disconnect.
    game.resolve_shot(0, 2, (9, 9))  # miss, turn -> 1
    sink_board(game, 1, 2)  # seat 1 eliminates seat 2 (kill bonus 3)
    assert game.players[1].score == 3
    # seat 1 had a hit so keeps the turn; miss to pass to... only 0 and 1 alive.
    game.resolve_shot(1, 0, (9, 9))
    assert game.turn == 0

    game.eliminate(1)  # seat 1 drops out

    assert game.alive[1] is False
    assert game.players[1].score == 3  # frozen, not voided
    assert game.is_over is True  # only seat 0 remains
    assert game.winner == 0


def test_public_snapshot_hides_afloat_ships_but_reveals_sunk_ones():
    game = Skirmish(make_players(2))
    game.resolve_shot(0, 1, (0, 1))  # hit but not sunk (2-cell boat)

    snap = game.public_snapshot()
    board1 = snap["boards"][1]

    assert board1["ships_left"] == 1
    assert board1["sunk"] == []  # not sunk yet -> no positions revealed
    assert [0, 1, True] in board1["shots"]
    assert snap["turn"] == 0
    assert snap["extra"] is True


# --- Energy economy / specials (Phase 1: generic cast pathway only) --------


def test_passive_energy_gain_is_granted_once_per_turn_not_on_a_chained_bonus_shot():
    game = Skirmish(make_players(3))

    game.resolve_shot(0, 1, (0, 1))  # hit -> extra shot, same turn continues
    assert game.players[0].energy == 1

    game.resolve_shot(0, 2, (0, 2))  # still seat 0's turn (chained bonus shot)
    assert game.players[0].energy == 1  # not re-granted


def test_retaliation_gain_is_credited_when_a_shot_lands_a_hit():
    game = Skirmish(make_players(3))

    game.resolve_shot(0, 1, (0, 1))  # hits P1's boat

    assert game.players[1].energy == 1


def test_retaliation_gain_is_not_credited_on_a_miss():
    game = Skirmish(make_players(3))

    game.resolve_shot(0, 1, (9, 9))  # empty water

    assert game.players[1].energy == 0


def test_resolve_cast_rejects_when_it_is_not_your_turn():
    players = make_players(3)
    players[0].country = "USA"
    game = Skirmish(players)

    outcome = game.resolve_cast(1)

    assert outcome.valid is False
    assert outcome.reason == "not your turn"


def test_resolve_cast_rejects_an_unknown_special_country():
    game = Skirmish(make_players(3))  # make_players leaves country=None

    outcome = game.resolve_cast(0)

    assert outcome.valid is False
    assert outcome.reason == "unknown special"


def test_resolve_cast_rejects_when_energy_is_insufficient():
    players = make_players(3)
    players[0].country = "Congo"  # costs 4; still the generic always-eligible placeholder handler
    game = Skirmish(players)

    outcome = game.resolve_cast(0)

    assert outcome.valid is False
    assert outcome.reason == "not enough energy"
    assert game.players[0].energy == 0  # rejected cast mutates nothing
    assert game.turn == 0  # turn not consumed


def test_cast_can_spend_the_passive_gain_granted_the_same_turn():
    players = make_players(3)
    players[0].country = "Congo"  # costs 4
    game = Skirmish(players)
    game.players[0].energy = 3  # one short of the cost before this turn's gain

    outcome = game.resolve_cast(0)

    assert outcome.valid is True
    assert game.players[0].energy == 0  # 3 + 1 (this turn's gain) - 4 (cost)


def test_valid_cast_deducts_cost_ends_turn_and_never_grants_a_bonus_shot():
    players = make_players(3)
    players[0].country = "Congo"  # costs 4
    game = Skirmish(players)
    game.players[0].energy = 10

    outcome = game.resolve_cast(0, payload={})

    assert outcome.valid is True
    assert outcome.special == "Congo"
    assert outcome.cost == 4
    assert game.players[0].energy == 10 + 1 - 4  # passive gain then cost
    assert game.extra is False
    assert game.turn == 1  # advanced, no bonus shot


def test_public_snapshot_exposes_energy():
    game = Skirmish(make_players(2))
    game.players[0].energy = 3

    snap = game.public_snapshot()

    assert snap["boards"][0]["energy"] == 3
