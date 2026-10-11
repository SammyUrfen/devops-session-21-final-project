"""Tests for the hand-drawn community maze guard in app/maze.py.

A generated grid already satisfies every structural rule a drawn grid must satisfy, so each case
starts from one and breaks exactly one rule. That keeps the failure attributable to one check.
"""

from app.maze import (
    WALL_E,
    WALL_N,
    WALL_S,
    WALL_W,
    check_drawn_grid,
    derived_difficulty,
    generate,
)

SEED = 20241012  # Fixed so a failure is reproducible.


def _good(width: int = 8, height: int = 8) -> list[list[int]]:
    return generate(width, height, SEED)


def test_a_good_drawn_grid_passes():
    assert check_drawn_grid(8, 8, _good()) is None


def test_size_outside_the_range_is_rejected():
    assert "between 4 and 20" in check_drawn_grid(2, 2, _good(2, 2))
    assert "between 4 and 20" in check_drawn_grid(21, 21, _good(21, 21))


def test_grid_shape_must_match_the_declared_size():
    assert "does not match" in check_drawn_grid(8, 8, _good(8, 7))
    assert "does not match" in check_drawn_grid(8, 8, [row[:-1] for row in _good()])


def test_a_value_above_fifteen_is_rejected():
    grid = _good()
    grid[3][3] = 16
    assert "0 and 15" in check_drawn_grid(8, 8, grid)


def test_a_non_integer_value_is_rejected():
    grid = _good()
    grid[2][2] = "7"
    assert "0 and 15" in check_drawn_grid(8, 8, grid)


def test_an_open_border_is_rejected():
    grid = _good()
    grid[0][0] &= ~WALL_N  # a hole in the top edge
    assert "border" in check_drawn_grid(8, 8, grid)


def test_neighbours_that_disagree_are_rejected():
    grid = _good()
    grid[0][0] ^= WALL_E  # one side only, so (0,0) and (1,0) now disagree
    assert "disagree" in check_drawn_grid(8, 8, grid)


def test_an_unsolvable_grid_is_rejected():
    grid = _good()
    # Seal the entrance on every side and close the matching side of both neighbours, so the only
    # broken rule is reachability.
    grid[0][0] = WALL_N | WALL_E | WALL_S | WALL_W
    grid[0][1] |= WALL_W
    grid[1][0] |= WALL_N
    assert "no path" in check_drawn_grid(8, 8, grid)


def test_derived_difficulty_follows_the_path_length():
    assert derived_difficulty(19) == "EASY"
    assert derived_difficulty(20) == "MEDIUM"
    assert derived_difficulty(44) == "MEDIUM"
    assert derived_difficulty(45) == "HARD"
