"""Maze generator, solver and invariant guard. Written from scratch, no third-party code.

Wall bitmask convention
-----------------------
One integer holds the four walls of one cell, so a grid is a plain list of lists of ints and
serialises to JSON with no encoder. A set bit means a wall is present:

    N = 1 (y - 1)   E = 2 (x + 1)   S = 4 (y + 1)   W = 8 (x - 1)

A full cell is 15. Carving clears the bit on both sides of the shared wall, so the two cells never
disagree about the wall between them. Indexing is ``grid[y][x]``.
"""

from __future__ import annotations

import random
from collections import deque

WALL_N = 1
WALL_E = 2
WALL_S = 4
WALL_W = 8
ALL_WALLS = WALL_N | WALL_E | WALL_S | WALL_W

# (dx, dy, wall leaving this cell, wall facing back from the neighbour)
_MOVES: tuple[tuple[int, int, int, int], ...] = (
    (0, -1, WALL_N, WALL_S),
    (1, 0, WALL_E, WALL_W),
    (0, 1, WALL_S, WALL_N),
    (-1, 0, WALL_W, WALL_E),
)

# Difficulty to grid size. Frozen by the API contract in PLAN.md section 3.
SIZES: dict[str, tuple[int, int]] = {"EASY": (8, 8), "MEDIUM": (14, 14), "HARD": (20, 20)}

# A seed must survive a round trip through a BigInteger column, so keep it inside signed 63 bits.
SEED_MAX = 2**62

Grid = list[list[int]]
Cell = tuple[int, int]


def entrance() -> Cell:
    """The player always starts top-left."""
    return (0, 0)


def exit_cell(width: int, height: int) -> Cell:
    """The goal is always bottom-right."""
    return (width - 1, height - 1)


def new_seed(rng: random.Random | None = None) -> int:
    """A fresh seed for a published maze. The server picks it, never the client."""
    return (rng or random).randrange(SEED_MAX)


def generate(width: int, height: int, seed: int) -> Grid:
    """Carve a perfect maze with a randomized depth-first search (recursive backtracker).

    The walk is iterative with an explicit stack. A 20x20 grid would not overflow CPython's limit,
    but an explicit stack costs nothing and keeps a larger size safe.

    Why the result is always a perfect maze: the carve visits each cell exactly once and opens a
    wall only when it moves into an unvisited cell. The opened walls therefore form a spanning tree
    over the cells. A tree has no cycle and is connected, so exactly one simple path joins any two
    cells, and no area is cut off. The outer border is never touched, because a move outside the
    grid is rejected before the wall is cleared.
    """
    if width < 1 or height < 1:
        raise ValueError(f"maze size must be positive, got {width}x{height}")

    rng = random.Random(seed)
    grid: Grid = [[ALL_WALLS] * width for _ in range(height)]
    visited = [[False] * width for _ in range(height)]

    start = entrance()
    visited[start[1]][start[0]] = True
    stack: list[Cell] = [start]

    while stack:
        x, y = stack[-1]
        candidates = [
            (nx, ny, out_wall, back_wall)
            for dx, dy, out_wall, back_wall in _MOVES
            for nx, ny in ((x + dx, y + dy),)
            if 0 <= nx < width and 0 <= ny < height and not visited[ny][nx]
        ]
        if not candidates:
            stack.pop()  # Dead end: backtrack.
            continue
        nx, ny, out_wall, back_wall = rng.choice(candidates)
        grid[y][x] &= ~out_wall
        grid[ny][nx] &= ~back_wall
        visited[ny][nx] = True
        stack.append((nx, ny))

    return grid


def neighbours(grid: Grid, x: int, y: int) -> list[Cell]:
    """The cells reachable from (x, y) in one step, that is, with no wall in between."""
    height = len(grid)
    width = len(grid[0])
    open_cells = []
    for dx, dy, out_wall, _back in _MOVES:
        if grid[y][x] & out_wall:
            continue
        nx, ny = x + dx, y + dy
        if 0 <= nx < width and 0 <= ny < height:
            open_cells.append((nx, ny))
    return open_cells


def solve(grid: Grid) -> list[Cell]:
    """Shortest path from the entrance to the exit, by breadth-first search.

    Returns the cells in order, entrance first and exit last. Returns an empty list when the exit
    cannot be reached. BFS, not DFS, because the path length is stored as ``solution_length`` and
    the cheat guard compares a player's move count against it, so it has to be the true minimum.
    """
    height = len(grid)
    width = len(grid[0])
    start = entrance()
    goal = exit_cell(width, height)

    came_from: dict[Cell, Cell | None] = {start: None}
    queue: deque[Cell] = deque([start])
    while queue:
        cell = queue.popleft()
        if cell == goal:
            path = [cell]
            while (previous := came_from[path[-1]]) is not None:
                path.append(previous)
            path.reverse()
            return path
        for nxt in neighbours(grid, *cell):
            if nxt not in came_from:
                came_from[nxt] = cell
                queue.append(nxt)
    return []


def reachable_count(grid: Grid) -> int:
    """How many cells can be reached from the entrance. A perfect maze reaches every cell."""
    start = entrance()
    seen = {start}
    stack = [start]
    while stack:
        for nxt in neighbours(grid, *stack.pop()):
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return len(seen)


def generate_verified(width: int, height: int, seed: int) -> tuple[Grid, list[Cell]]:
    """Generate, then prove the two invariants before the grid can reach the database.

    1. The solver finds a path from the entrance to the exit.
    2. Every cell is reachable, so the carve really produced a spanning tree.

    A stored maze that fails either one is unplayable, and the cheat guard would compare against a
    meaningless length. Failing loudly here is cheaper than finding it in the browser.
    """
    grid = generate(width, height, seed)
    path = solve(grid)
    if not path:
        raise MazeInvariantError(f"no path from entrance to exit in {width}x{height} seed {seed}")
    reached = reachable_count(grid)
    if reached != width * height:
        raise MazeInvariantError(
            f"{width * height - reached} of {width * height} cells unreachable, seed {seed}"
        )
    return grid, path


class MazeInvariantError(RuntimeError):
    """A generated grid failed the solver check or the reachability check."""


# --- Hand-drawn community mazes (PLAN.md section 11) ---------------------------------------------

# A drawn grid is not generated, so nothing but these bounds limits it. Below 4 a maze is not a
# maze, and 20 is the largest size the renderer and the HARD generator already handle.
MIN_DRAWN_SIZE = 4
MAX_DRAWN_SIZE = 20

# Derived difficulty badge for a drawn maze, keyed on the shortest path length. A drawn grid has no
# difficulty of its own, so the label comes from how far the player must walk.
COMMUNITY_MEDIUM_FROM = 20
COMMUNITY_HARD_FROM = 45


def derived_difficulty(solution_length: int) -> str:
    """The badge of a drawn maze. The label is cosmetic, it never changes the grid."""
    if solution_length >= COMMUNITY_HARD_FROM:
        return "HARD"
    if solution_length >= COMMUNITY_MEDIUM_FROM:
        return "MEDIUM"
    return "EASY"


def check_drawn_grid(width: int, height: int, grid: object) -> str | None:
    """Return the reason a hand-drawn grid is unacceptable, or None when every check passes.

    The client draws the grid, so the whole payload is untrusted input. Each check names what it
    stops, because the browser shows this sentence to the person who drew the maze.
    """
    # 1. Size. An unbounded width or height lets one request allocate an arbitrary grid and makes
    #    every later loop as long as the attacker likes. Reject before anything is indexed.
    if not (MIN_DRAWN_SIZE <= width <= MAX_DRAWN_SIZE and MIN_DRAWN_SIZE <= height <= MAX_DRAWN_SIZE):
        return (
            f"size {width}x{height} is out of range, width and height must be "
            f"between {MIN_DRAWN_SIZE} and {MAX_DRAWN_SIZE}"
        )
    if (
        not isinstance(grid, list)
        or len(grid) != height
        or any(not isinstance(row, list) or len(row) != width for row in grid)
    ):
        return f"the grid shape does not match the declared size of {width}x{height}"

    # 2. Cell values. A value outside 0..15 means stray bits the renderer and the solver both
    #    ignore, so the stored grid would not be the grid anybody drew or plays. A bool is an int
    #    in Python, and True would silently become the wall mask 1.
    for y, row in enumerate(grid):
        for x, value in enumerate(row):
            if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= ALL_WALLS:
                return f"cell ({x}, {y}) is {value!r}, every value must be an integer between 0 and 15"

    # 3. Closed border. An open border lets the player walk off the grid, which the play canvas
    #    guards against but no stored maze should ever require.
    for x in range(width):
        if not grid[0][x] & WALL_N:
            return f"the border is open at the top of column {x}, an outer wall cannot be removed"
        if not grid[height - 1][x] & WALL_S:
            return f"the border is open at the bottom of column {x}, an outer wall cannot be removed"
    for y in range(height):
        if not grid[y][0] & WALL_W:
            return f"the border is open at the left of row {y}, an outer wall cannot be removed"
        if not grid[y][width - 1] & WALL_E:
            return f"the border is open at the right of row {y}, an outer wall cannot be removed"

    # 4. Neighbours agree. This is the check a drawing tool breaks most often: it flips one side of
    #    a shared wall and forgets the other. The solver would then find a path through a wall the
    #    renderer still draws, so the player sees a maze that cannot be walked.
    for y in range(height):
        for x in range(width):
            if x + 1 < width and bool(grid[y][x] & WALL_E) != bool(grid[y][x + 1] & WALL_W):
                return f"cells ({x}, {y}) and ({x + 1}, {y}) disagree about the wall between them"
            if y + 1 < height and bool(grid[y][x] & WALL_S) != bool(grid[y + 1][x] & WALL_N):
                return f"cells ({x}, {y}) and ({x}, {y + 1}) disagree about the wall between them"

    # 5. A path exists. Without this a maze could be published that nobody can finish, and
    #    solution_length would be zero, which would disable the cheat guard on completions.
    if not solve(grid):
        return "no path leads from the entrance to the exit, the maze cannot be finished"
    return None
