"""Tests for the from-scratch generator and solver in app/maze.py."""

from itertools import pairwise

from app.maze import SIZES, generate, generate_verified, reachable_count, solve

SEED = 20241012  # Fixed so a failure is reproducible.


def test_every_cell_is_reachable():
    """A depth-first carve is a spanning tree, so the whole grid must be one component."""
    grid = generate(14, 14, SEED)
    assert reachable_count(grid) == 14 * 14


def test_same_seed_gives_the_same_grid():
    assert generate(8, 8, SEED) == generate(8, 8, SEED)
    assert generate(8, 8, SEED) != generate(8, 8, SEED + 1)


def test_solver_length_matches_the_path():
    grid = generate(20, 20, SEED)
    path = solve(grid)
    assert path[0] == (0, 0)
    assert path[-1] == (19, 19)
    # Each step moves exactly one cell on one axis.
    for (x1, y1), (x2, y2) in pairwise(path):
        assert abs(x1 - x2) + abs(y1 - y2) == 1
    assert len(generate_verified(20, 20, SEED)[1]) == len(path)


def test_sizes_match_the_contract():
    assert SIZES == {"EASY": (8, 8), "MEDIUM": (14, 14), "HARD": (20, 20)}
