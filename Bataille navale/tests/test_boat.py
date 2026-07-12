from battleship.models.boat import Boat


def test_default_name_falls_back_to_type():
    boat = Boat(3, [(0, 0), (0, 1), (0, 2)])

    assert boat.name == boat.type == "sous-marin"


def test_custom_name_is_kept_as_given():
    boat = Boat(3, [(0, 0), (0, 1), (0, 2)], name="Titanic")

    assert boat.name == "Titanic"
    assert boat.type == "sous-marin"  # type is still derived from size, independent of the custom name


def test_register_hit_marks_cell_and_reduces_health():
    boat = Boat(2, [(0, 0), (0, 1)])

    hit, sunk = boat.register_hit((0, 0))

    assert hit is True
    assert sunk is False
    assert boat.hits_remaining == 1
    assert boat.is_sunk is False


def test_register_hit_sinks_when_all_cells_hit():
    boat = Boat(2, [(0, 0), (0, 1)])
    boat.register_hit((0, 0))

    hit, sunk = boat.register_hit((0, 1))

    assert hit is True
    assert sunk is True
    assert boat.is_sunk is True


def test_register_hit_miss_does_not_change_state():
    boat = Boat(2, [(0, 0), (0, 1)])

    hit, sunk = boat.register_hit((5, 5))

    assert hit is False
    assert sunk is False
    assert boat.hits_remaining == 2


def test_register_hit_on_already_hit_cell_does_not_double_count():
    boat = Boat(2, [(0, 0), (0, 1)])
    boat.register_hit((0, 0))

    hit, sunk = boat.register_hit((0, 0))

    assert hit is False
    assert boat.hits_remaining == 1
