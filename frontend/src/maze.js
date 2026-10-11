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

// --- Hand drawing (PLAN.md section 11) ---
// A drawn grid starts with every wall closed and the person opens the ones they want. The two
// cells beside a wall must always agree, so every toggle flips both sides. The server repeats the
// same checks in app/maze.py, so a bug here cannot publish a broken maze.

export const ALL_WALLS = WALL_N | WALL_E | WALL_S | WALL_W; // a cell sealed on every side

// The wall facing back from the neighbour, for each side of a cell.
const OPPOSITE = { N: 'S', E: 'W', S: 'N', W: 'E' };

/** A drawing grid of `width` x `height` cells with every wall in place. */
export function closedGrid(width, height) {
  return Array.from({ length: height }, () => Array.from({ length: width }, () => ALL_WALLS));
}

/** True when `dir` of (x,y) is an outer edge of the grid, which must stay closed. */
export function isBorderEdge(width, height, x, y, dir) {
  const d = DIRECTIONS[dir];
  if (!d) return false;
  const tx = x + d.dx;
  const ty = y + d.dy;
  return tx < 0 || ty < 0 || tx >= width || ty >= height;
}

/** Flip the wall on `dir` of (x,y) and the matching side of its neighbour.
 *
 * Returns a new grid, or null when the edge is on the border. Null rather than an unchanged grid,
 * so the Draw view can tell the difference and say why nothing happened.
 */
export function toggleWall(grid, x, y, dir) {
  const height = grid.length;
  const width = grid[0].length;
  if (!DIRECTIONS[dir] || grid[y]?.[x] === undefined) return null;
  if (isBorderEdge(width, height, x, y, dir)) return null;
  const next = grid.map((row) => row.slice());
  const target = step(x, y, dir);
  next[y][x] ^= DIRECTIONS[dir].bit;
  next[target.y][target.x] ^= DIRECTIONS[OPPOSITE[dir]].bit;
  return next;
}

/** Breadth-first search from (0,0) to the bottom-right cell, run in the browser.
 *
 * Breadth-first, not depth-first, because the reported length must be the shortest path: the
 * server stores that number and its cheat guard rejects any run below it.
 */
export function solveLocal(grid) {
  const height = grid.length;
  const width = grid[0].length;
  const goal = `${width - 1},${height - 1}`;
  const distance = new Map([['0,0', 1]]); // path length in cells, so the entrance counts as one
  const queue = [{ x: 0, y: 0 }];
  for (let head = 0; head < queue.length; head += 1) {
    const { x, y } = queue[head];
    const here = distance.get(`${x},${y}`);
    if (`${x},${y}` === goal) return { solvable: true, length: here };
    for (const dir of Object.keys(DIRECTIONS)) {
      if (!canMove(grid, x, y, dir)) continue;
      const next = step(x, y, dir);
      const key = `${next.x},${next.y}`;
      if (distance.has(key)) continue;
      distance.set(key, here + 1);
      queue.push(next);
    }
  }
  return { solvable: false, length: 0 };
}
