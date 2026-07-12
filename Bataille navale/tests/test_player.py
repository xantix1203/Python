from battleship.models.bot import Bot
from battleship.models.player import Player


def make_pair():
    shooter = Player("Alice")
    target = Player("Bob")
    shooter.register_opponent(target)
    target.register_opponent(shooter)
    return shooter, target


def test_fire_scores_one_point_on_hit():
    shooter, target = make_pair()
    target.grid.place(0, 0, 2, (0, 1))

    hit, sunk_boat = shooter.fire(target, (0, 0))

    assert hit is True
    assert sunk_boat is None
    assert shooter.score == 1


def test_fire_scores_bonus_point_on_sink():
    shooter, target = make_pair()
    target.grid.place(0, 0, 2, (0, 1))
    shooter.fire(target, (0, 0))

    hit, sunk_boat = shooter.fire(target, (0, 1))

    assert hit is True
    assert sunk_boat is not None
    assert shooter.score == 3  # two hits + one sink bonus


def test_fire_on_miss_scores_nothing_but_still_records_shot():
    shooter, target = make_pair()

    hit, sunk_boat = shooter.fire(target, (9, 9))

    assert hit is False
    assert sunk_boat is None
    assert shooter.score == 0
    assert (9, 9) in shooter.shots_fired[target]


def test_has_fired_at_reflects_recorded_shots():
    shooter, target = make_pair()

    assert shooter.has_fired_at(target, (3, 3)) is False
    shooter.fire(target, (3, 3))
    assert shooter.has_fired_at(target, (3, 3)) is True


def test_bot_get_shot_never_repeats_a_cell():
    bot = Bot()
    opponent = Player("Target")
    bot.register_opponent(opponent)

    seen = set()
    for _ in range(100):
        shot = bot.get_shot(opponent)
        assert shot not in seen
        seen.add(shot)
