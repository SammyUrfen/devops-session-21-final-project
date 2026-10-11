// Checks the wall-bitmask reading used by the play canvas. Run: node --test src/maze.test.mjs
import test from 'node:test';
import assert from 'node:assert/strict';
import { DIRECTIONS, wallsOf, canMove, step } from './maze.js';

const ALL_WALLS = 15; // N|E|S|W, a cell sealed on every side
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
