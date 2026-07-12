from battleship.config import BOARD_SIZE
from battleship.models.bot import Bot
from battleship.models.player import Player


def make_bot_and_opponent():
    bot = Bot()
    opponent = Player("Target")
    bot.register_opponent(opponent)
    return bot, opponent


def test_hit_makes_the_next_shot_target_a_neighbor():
    bot, opponent = make_bot_and_opponent()

    bot.record_shot_result(opponent, (5, 5), hit=True, sunk_boat=None)
    shot = bot.get_shot(opponent)

    assert shot in {(6, 5), (4, 5), (5, 6), (5, 4)}


def test_sinking_a_boat_clears_the_hunt_stack():
    bot, opponent = make_bot_and_opponent()
    bot.record_shot_result(opponent, (5, 5), hit=True, sunk_boat=None)

    bot.record_shot_result(opponent, (6, 5), hit=True, sunk_boat=object())

    assert bot._hunt_stacks[opponent] == []


def test_hunt_neighbors_near_the_edge_stay_in_bounds():
    bot, opponent = make_bot_and_opponent()

    bot.record_shot_result(opponent, (0, 0), hit=True, sunk_boat=None)

    for x, y in bot._hunt_stacks[opponent]:
        assert 0 <= x < BOARD_SIZE
        assert 0 <= y < BOARD_SIZE


def test_get_shot_never_repeats_a_cell_even_while_hunting():
    bot, opponent = make_bot_and_opponent()

    seen = set()
    for i in range(100):
        shot = bot.get_shot(opponent)
        assert shot not in seen
        seen.add(shot)
        bot.record_shot_result(opponent, shot, hit=(i % 2 == 0), sunk_boat=None)
