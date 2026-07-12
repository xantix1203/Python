from battleship.config import BOARD_SIZE, FLEET
from battleship.models.grid import Grid


def test_place_fleet_randomly_places_full_fleet_without_overlap():
    grid = Grid()

    grid.place_fleet_randomly()

    expected_boat_count = sum(FLEET.values())
    expected_cell_count = sum(size * count for size, count in FLEET.items())
    all_cells = [cell for boat in grid.floating_boats for cell, _ in boat.cells]

    assert len(grid.floating_boats) == expected_boat_count
    assert len(all_cells) == expected_cell_count
    assert len(set(all_cells)) == expected_cell_count  # no overlap


def test_can_place_rejects_out_of_bounds():
    grid = Grid()

    assert grid.can_place(BOARD_SIZE - 1, BOARD_SIZE - 1, 3, (1, 0)) is False


def test_can_place_rejects_overlap_with_existing_boat():
    grid = Grid()
    grid.place(0, 0, 3, (0, 1))  # occupies (0,0), (0,1), (0,2)

    assert grid.can_place(0, 2, 2, (1, 0)) is False


def test_can_place_allows_adjacent_non_overlapping_boat():
    grid = Grid()
    grid.place(0, 0, 3, (0, 1))  # occupies (0,0), (0,1), (0,2)

    assert grid.can_place(1, 0, 2, (0, 1)) is True


def test_register_shot_hit_then_miss():
    grid = Grid()
    grid.place(0, 0, 2, (0, 1))  # occupies (0,0), (0,1)

    hit, sunk_boat = grid.register_shot((0, 0))
    assert hit is True
    assert sunk_boat is None

    hit, sunk_boat = grid.register_shot((5, 5))
    assert hit is False
    assert sunk_boat is None


def test_register_shot_sinks_and_moves_boat_to_sunk_list():
    grid = Grid()
    grid.place(0, 0, 2, (0, 1))
    grid.register_shot((0, 0))

    hit, sunk_boat = grid.register_shot((0, 1))

    assert hit is True
    assert sunk_boat is not None
    assert grid.floating_boats == []
    assert sunk_boat in grid.sunk_boats
