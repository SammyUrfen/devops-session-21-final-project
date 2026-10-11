// Wall-bitmask helpers for the MazeHub play canvas.
// The backend sends `grid` as height rows of width ints. Each int is the wall
// bitmask of that cell: a set bit means a wall on that side, so a move is legal
// only when the bit is clear AND the target cell is inside the grid.
// Pure functions, no DOM, so node --test can check them.

export const WALL_N = 1;
export const WALL_E = 2;
export const WALL_S = 4;
export const WALL_W = 8;

// Bit to test, and the cell offset taken when that side is open.
export const DIRECTIONS = {
  N: { bit: WALL_N, dx: 0, dy: -1 },
  E: { bit: WALL_E, dx: 1, dy: 0 },
  S: { bit: WALL_S, dx: 0, dy: 1 },
  W: { bit: WALL_W, dx: -1, dy: 0 },
};

/** Split one cell's bitmask into the four sides that need a drawn line. */
export function wallsOf(mask) {
  return {
    n: (mask & WALL_N) !== 0,
    e: (mask & WALL_E) !== 0,
    s: (mask & WALL_S) !== 0,
    w: (mask & WALL_W) !== 0,
  };
}

/** The cell one step away in `dir`. Does not check that it exists. */
export function step(x, y, dir) {
  const d = DIRECTIONS[dir];
  return { x: x + d.dx, y: y + d.dy };
}

/** True when the player at (x,y) may walk one cell in `dir`. */
export function canMove(grid, x, y, dir) {
  const d = DIRECTIONS[dir];
  if (!d) return false;
  const row = grid?.[y];
  if (row === undefined || row[x] === undefined) return false;
  if ((row[x] & d.bit) !== 0) return false; // a wall stands on that side
  const target = step(x, y, dir);
  // A border cell can carry a clear bit in malformed data, so check the bounds too.
  return grid[target.y] !== undefined && grid[target.y][target.x] !== undefined;
}

/** Flatten GET /api/mazes/stats into one tile per number, in server key order.
 *
 * by_difficulty is a nested object, so a plain Object.entries walk over the response puts an
 * object into a tile and the card reads "[object Object]". Each nested count becomes its own tile,
 * labelled by its inner key, and a new top-level counter still needs no change here.
 */
export function statTiles(stats) {
  if (!stats || typeof stats !== 'object') return [];
  return Object.entries(stats).flatMap(([key, value]) =>
    value && typeof value === 'object'
      ? Object.entries(value).map(([inner, count]) => ({ label: inner.toLowerCase(), value: count }))
      : [{ label: key.replace(/_/g, ' '), value }],
  );
}
