// Checks the wall-bitmask reading used by the play canvas. Run: node --test src/maze.test.mjs
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  ALL_WALLS, DIRECTIONS, WALL_E, WALL_W, canMove, closedGrid, solveLocal, statTiles, step,
  toggleWall, wallsOf,
} from './maze.js';

const OPEN = 0; // no wall on any side

test('a closed cell blocks every direction', () => {
  const grid = [
    [ALL_WALLS, ALL_WALLS],
    [ALL_WALLS, ALL_WALLS],
  ];
  assert.deepEqual(wallsOf(ALL_WALLS), { n: true, e: true, s: true, w: true });
  for (const dir of Object.keys(DIRECTIONS)) {
    assert.equal(canMove(grid, 0, 0, dir), false, `${dir} must be blocked`);
  }
});

test('an open side allows the move', () => {
  // Cell (0,0) has walls on N and W only, so E and S are clear.
  const grid = [
    [1 | 8, OPEN],
    [OPEN, OPEN],
  ];
  assert.deepEqual(wallsOf(1 | 8), { n: true, e: false, s: false, w: true });
  assert.equal(canMove(grid, 0, 0, 'E'), true);
  assert.equal(canMove(grid, 0, 0, 'S'), true);
  assert.deepEqual(step(0, 0, 'E'), { x: 1, y: 0 });
  assert.deepEqual(step(0, 0, 'S'), { x: 0, y: 1 });
});

test('a move off the border is refused even with no wall bit', () => {
  const grid = [
    [OPEN, OPEN],
    [OPEN, OPEN],
  ];
  assert.equal(canMove(grid, 0, 0, 'N'), false, 'north of the top row is outside');
  assert.equal(canMove(grid, 0, 0, 'W'), false, 'west of the left column is outside');
  assert.equal(canMove(grid, 1, 1, 'E'), false, 'east of the last column is outside');
  assert.equal(canMove(grid, 1, 1, 'S'), false, 'south of the last row is outside');
});

test('stat tiles flatten the nested by_difficulty counts', () => {
  // The real shape of GET /api/mazes/stats. by_difficulty is an object, so a plain
  // Object.entries walk renders "[object Object]" in a tile.
  const tiles = statTiles({
    total: 3,
    by_difficulty: { EASY: 1, MEDIUM: 0, HARD: 2 },
    completions: 4,
    authors: 2,
  });
  assert.deepEqual(tiles, [
    { label: 'total', value: 3 },
    { label: 'easy', value: 1 },
    { label: 'medium', value: 0 },
    { label: 'hard', value: 2 },
    { label: 'completions', value: 4 },
    { label: 'authors', value: 2 },
  ]);
  for (const tile of tiles) assert.equal(typeof tile.value, 'number', `${tile.label} must be a number`);
});

test('stat tiles of nothing is an empty list', () => {
  assert.deepEqual(statTiles(null), []);
});

// --- The hand-drawing helpers (PLAN.md section 11) ---

test('a fresh drawing grid has every wall closed', () => {
  const grid = closedGrid(4, 3);
  assert.equal(grid.length, 3);
  assert.equal(grid[0].length, 4);
  assert.ok(grid.every((row) => row.every((mask) => mask === ALL_WALLS)));
});

test('a toggle changes both sides of the shared wall', () => {
  const next = toggleWall(closedGrid(2, 2), 0, 0, 'E');
  assert.equal(next[0][0] & WALL_E, 0, 'the east wall of (0,0) is gone');
  assert.equal(next[0][1] & WALL_W, 0, 'the west wall of (1,0) is gone too');
  // The other sides are untouched, so the border stays closed.
  assert.equal(next[0][0], ALL_WALLS - WALL_E);
  assert.equal(next[0][1], ALL_WALLS - WALL_W);
});

test('toggling twice returns the start state', () => {
  const start = closedGrid(3, 3);
  const once = toggleWall(start, 1, 1, 'S');
  assert.notDeepEqual(once, start);
  assert.deepEqual(toggleWall(once, 1, 1, 'S'), start);
  // The neighbour side also flips back, so the grids compare equal cell by cell.
  assert.deepEqual(toggleWall(once, 1, 2, 'N'), start);
});

test('a border wall cannot be toggled', () => {
  const grid = closedGrid(3, 3);
  assert.equal(toggleWall(grid, 0, 0, 'N'), null, 'north of the top row is the border');
  assert.equal(toggleWall(grid, 0, 0, 'W'), null, 'west of the left column is the border');
  assert.equal(toggleWall(grid, 2, 2, 'E'), null);
  assert.equal(toggleWall(grid, 2, 2, 'S'), null);
});

test('the local search agrees with a known small grid', () => {
  // A sealed 3x3 has no route at all.
  let grid = closedGrid(3, 3);
  assert.deepEqual(solveLocal(grid), { solvable: false, length: 0 });
  // Carve the L route (0,0) -> (1,0) -> (2,0) -> (2,1) -> (2,2): five cells, four moves.
  grid = toggleWall(grid, 0, 0, 'E');
  grid = toggleWall(grid, 1, 0, 'E');
  grid = toggleWall(grid, 2, 0, 'S');
  grid = toggleWall(grid, 2, 1, 'S');
  assert.deepEqual(solveLocal(grid), { solvable: true, length: 5 });
  // A second, shorter route down the middle makes it four cells.
  grid = toggleWall(grid, 0, 0, 'S');
  grid = toggleWall(grid, 0, 1, 'S');
  grid = toggleWall(grid, 0, 2, 'E');
  grid = toggleWall(grid, 1, 2, 'E');
  assert.deepEqual(solveLocal(grid), { solvable: true, length: 5 });
});
