import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';
import {
  WALL_E, WALL_S, canMove, closedGrid, isBorderEdge, solveLocal, statTiles, step,
  toggleWall, wallsOf,
} from './maze.js';

// Same-origin base path. Nginx (compose) and the Ingress (Kubernetes) both route /api
// to the backend, so the host must never appear here.
const API = '/api';

const PLAYER_KEY = 'mazehub.player';
const DIFFICULTIES = ['EASY', 'MEDIUM', 'HARD'];
const FILTERS = ['All', ...DIFFICULTIES];

// The gallery tabs map one to one onto the `source` query of GET /api/mazes, so a drawn maze never
// appears beside a generated one. See PLAN.md section 11.
const TABS = [
  { key: 'GENERATED', label: 'Generated' },
  { key: 'COMMUNITY', label: 'Community' },
];

// The sizes the Draw view offers. Both the client and the server accept 4 to 20, but a drawing
// larger than 16 is slow to click out by hand.
const DRAW_SIZES = [8, 12, 16];

// Arrow keys and WASD both move one cell. event.key is lower-cased before lookup.
const KEY_TO_DIRECTION = {
  arrowup: 'N', w: 'N',
  arrowright: 'E', d: 'E',
  arrowdown: 'S', s: 'S',
  arrowleft: 'W', a: 'W',
};

/** Read a JSON body, or throw a message the UI can show. */
async function request(path, options) {
  let res;
  try {
    res = await fetch(`${API}${path}`, options);
  } catch {
    throw new Error('The backend did not answer');
  }
  if (!res.ok) throw new Error(await errorMessage(res));
  return res.status === 204 ? null : res.json();
}

/** FastAPI returns {detail: string} or {detail: [{msg}]}. Flatten either into one line. */
async function errorMessage(res) {
  let detail;
  try {
    detail = (await res.json()).detail;
  } catch {
    detail = null;
  }
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map((d) => d.msg || JSON.stringify(d)).join('; ');
  return `Request failed with status ${res.status}`;
}

function jsonPost(method, body) {
  return { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) };
}

function App() {
  const [player, setPlayer] = useState(() => localStorage.getItem(PLAYER_KEY) || '');
  const [view, setView] = useState('gallery');
  const [playing, setPlaying] = useState(null); // the maze id open in the play view
  const [tab, setTab] = useState(TABS[0].key); // which gallery tab is open

  const savePlayer = (name) => {
    localStorage.setItem(PLAYER_KEY, name);
    setPlayer(name);
  };

  if (!player) return <NameGate onSave={savePlayer} />;

  const open = (id) => { setPlaying(id); setView('play'); };
  const backToGallery = () => { setPlaying(null); setView('gallery'); };
  // After a drawing is published the Community tab is the only place it appears.
  const afterDraw = () => { setTab('COMMUNITY'); backToGallery(); };

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">◼</span>
          <div><b>MazeHub</b><small>maze gallery</small></div>
        </div>
        <nav>
          <a className={view === 'gallery' || view === 'play' ? 'active' : ''} onClick={backToGallery}>▦ <span>Gallery</span></a>
          <a className={view === 'publish' ? 'active' : ''} onClick={() => setView('publish')}>＋ <span>Publish</span></a>
          <a className={view === 'draw' ? 'active' : ''} onClick={() => setView('draw')}>✎ <span>Draw</span></a>
          <a className={view === 'completed' ? 'active' : ''} onClick={() => setView('completed')}>✓ <span>Completed</span></a>
        </nav>
        <div className="side-bottom">
          <div className="upgrade">
            <strong>How to play</strong>
            <p>Start at the top left. Walk to the bottom right with the arrow keys or WASD.</p>
          </div>
          <div className="profile">
            <span className="avatar">{player.slice(0, 2).toUpperCase()}</span>
            <div><b>{player}</b><small>stored in this browser</small></div>
            <button className="icon-btn" title="Change name" onClick={() => savePlayer('')}>✎</button>
          </div>
        </div>
      </aside>
      <main className="main">
        {view === 'gallery' && (
          <Gallery tab={tab} onTab={setTab} onPlay={open} onPublish={() => setView('publish')} onDraw={() => setView('draw')} />
        )}
        {view === 'draw' && <Draw author={player} onDone={afterDraw} onCancel={backToGallery} />}
        {view === 'play' && <Play mazeId={playing} player={player} onExit={backToGallery} />}
        {view === 'publish' && <Publish author={player} onDone={backToGallery} />}
        {view === 'completed' && <Completed player={player} />}
      </main>
    </div>
  );
}

function NameGate({ onSave }) {
  return (
    <div className="gate">
      <form
        className="modal"
        onSubmit={(e) => {
          e.preventDefault();
          const name = new FormData(e.currentTarget).get('player').trim();
          if (name) onSave(name);
        }}
      >
        <div className="modal-head">
          <div><p className="eyebrow">MAZEHUB</p><h2>What should we call you?</h2></div>
        </div>
        <p className="muted">No sign in. The name stays in this browser and labels the mazes you solve.</p>
        <label>Player name<input name="player" required autoFocus maxLength={40} placeholder="e.g. Explorer" /></label>
        <button className="primary full">Start</button>
      </form>
    </div>
  );
}

function Gallery({ tab, onTab, onPlay, onPublish, onDraw }) {
  const [mazes, setMazes] = useState([]);
  const [stats, setStats] = useState(null);
  const [filter, setFilter] = useState('All');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      // The difficulty chips apply to the generated tab only: a drawn maze carries a derived
      // badge, so filtering the community list by it would hide mazes for no reason the user set.
      const query = tab === 'GENERATED' && filter !== 'All'
        ? `?source=GENERATED&difficulty=${filter}`
        : `?source=${tab}`;
      const [list, counts] = await Promise.all([request(`/mazes${query}`), request('/mazes/stats')]);
      setMazes(list);
      setStats(counts);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [filter, tab]);
  useEffect(() => { load(); }, [load]);

  const remove = async (maze) => {
    if (!confirm(`Delete "${maze.title}" and its completions?`)) return;
    try {
      await request(`/mazes/${maze.id}`, { method: 'DELETE' });
      load();
    } catch (e) {
      setError(e.message);
    }
  };

  return (
    <>
      <header>
        <div>
          <p className="eyebrow">MAZEHUB / GALLERY</p>
          <h1>Pick a maze</h1>
          <p className="muted">Every grid is generated and checked on the server before it is published.</p>
        </div>
        <div className="card-actions">
          <button className="ghost" onClick={onDraw}>✎ Draw one</button>
          <button className="primary" onClick={onPublish}>＋ Publish a maze</button>
        </div>
      </header>
      <div className="filters tabs">
        {TABS.map((t) => (
          <button key={t.key} className={tab === t.key ? 'selected' : ''} onClick={() => onTab(t.key)}>{t.label}</button>
        ))}
      </div>
      {error && <ErrorBanner message={error} onRetry={load} />}
      {/* statTiles flattens the server's shape, including the nested by_difficulty counts. */}
      <section className="stats">
        {stats
          ? statTiles(stats).map((tile) => <Stat key={tile.label} label={tile.label} value={tile.value} />)
          : <div className="empty">Loading counts…</div>}
      </section>
      <section className="panel">
        <div className="panel-head">
          <div>
            <h2>{tab === 'GENERATED' ? 'Generated mazes' : 'Community mazes'}</h2>
            <p className="muted">
              {tab === 'GENERATED'
                ? 'Carved by the server from a seed. Shortest path is the fewest moves it will accept.'
                : 'Drawn by hand and checked by the server. The badge comes from the path length.'}
            </p>
          </div>
          {tab === 'GENERATED' && (
            <div className="filters">
              {FILTERS.map((f) => (
                <button key={f} className={filter === f ? 'selected' : ''} onClick={() => setFilter(f)}>{f}</button>
              ))}
            </div>
          )}
        </div>
        {loading ? <div className="empty">Loading mazes…</div> : (
          <div className="cards">
            {mazes.map((m) => (
              <article className="maze-card" key={m.id}>
                <div className="maze-card-top">
                  <b>{m.title}</b>
                  <span className={`priority ${m.difficulty.toLowerCase()}`}>{m.difficulty}</span>
                </div>
                <small>by {m.author}</small>
                <dl className="facts">
                  <div><dt>Size</dt><dd>{m.width}×{m.height}</dd></div>
                  <div><dt>Shortest path</dt><dd>{m.solution_length}</dd></div>
                  <div><dt>Completions</dt><dd>{m.completion_count}</dd></div>
                </dl>
                <div className="card-actions">
                  <button className="primary" onClick={() => onPlay(m.id)}>▶ Play</button>
                  <button className="ghost" onClick={() => remove(m)}>Delete</button>
                </div>
              </article>
            ))}
            {!mazes.length && !error && (
              <div className="empty">
                {tab === 'GENERATED' ? 'No mazes in this filter yet. Publish one.' : 'No drawn mazes yet. Open Draw and make one.'}
              </div>
            )}
          </div>
        )}
      </section>
    </>
  );
}

function Play({ mazeId, player, onExit }) {
  const [maze, setMaze] = useState(null);
  const [error, setError] = useState('');
  const [at, setAt] = useState({ x: 0, y: 0 });
  const [moves, setMoves] = useState(0);
  const [seconds, setSeconds] = useState(0);
  const [solution, setSolution] = useState(null);
  const [result, setResult] = useState(null); // the saved completion, or an error message
  const canvasRef = useRef(null);
  const boardRef = useRef(null);

  const finished = result !== null;
  const exit = maze ? { x: maze.width - 1, y: maze.height - 1 } : null;

  useEffect(() => {
    let live = true;
    request(`/mazes/${mazeId}`)
      .then((m) => { if (live) setMaze(m); })
      .catch((e) => { if (live) setError(e.message); });
    return () => { live = false; };
  }, [mazeId]);

  // The timer starts with the maze and stops as soon as a run is recorded.
  useEffect(() => {
    if (!maze || finished) return undefined;
    const id = setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => clearInterval(id);
  }, [maze, finished]);

  const submit = useCallback(async (totalMoves, totalSeconds) => {
    try {
      const completion = await request(`/mazes/${mazeId}/completions`, jsonPost('POST', {
        player, moves: totalMoves, seconds: totalSeconds,
      }));
      setResult({ completion });
    } catch (e) {
      // A run below solution_length comes back 422. Show the server's own words.
      setResult({ message: e.message });
    }
  }, [mazeId, player]);

  // Reads the live state instead of nesting state updaters: React StrictMode calls an
  // updater twice, which would count every move and every completion twice.
  const move = useCallback((dir) => {
    if (!maze || finished) return;
    if (!canMove(maze.grid, at.x, at.y, dir)) return;
    const next = step(at.x, at.y, dir);
    const total = moves + 1;
    setAt(next);
    setMoves(total);
    if (next.x === exit.x && next.y === exit.y) submit(total, seconds);
  }, [maze, finished, at, moves, seconds, exit, submit]);

  // The board div holds focus, so the arrow keys scroll nothing.
  useEffect(() => { boardRef.current?.focus(); }, [maze]);

  const onKeyDown = (e) => {
    const dir = KEY_TO_DIRECTION[e.key.toLowerCase()];
    if (!dir) return;
    e.preventDefault();
    move(dir);
  };

  const showSolution = async () => {
    try {
      const data = await request(`/mazes/${mazeId}/solution`);
      setSolution(normalisePath(data.path));
    } catch (e) {
      setError(e.message);
    }
  };

  useEffect(() => { draw(canvasRef.current, maze, at, solution); }, [maze, at, solution]);

  if (error) return <><PlayHeader onExit={onExit} /><ErrorBanner message={error} /></>;
  if (!maze) return <><PlayHeader onExit={onExit} /><div className="empty">Loading the maze…</div></>;

  return (
    <>
      <PlayHeader maze={maze} onExit={onExit} />
      <section className="stats">
        <Stat label="moves" value={moves} />
        <Stat label="seconds" value={seconds} />
        <Stat label="shortest path" value={maze.solution_length} />
        <Stat label="completions" value={maze.completion_count} />
      </section>
      <section className="panel play-panel">
        <div className="panel-head">
          <div>
            <h2>{maze.title}</h2>
            <p className="muted">Entrance is the top left square. The exit is marked at the bottom right.</p>
          </div>
          <div className="card-actions">
            <button className="ghost" onClick={showSolution}>Show solution</button>
            <button className="ghost" onClick={() => boardRef.current?.focus()}>Focus board</button>
          </div>
        </div>
        <div className="board" ref={boardRef} tabIndex={0} onKeyDown={onKeyDown}>
          <canvas ref={canvasRef} />
        </div>
        <p className="hint">Keys: ↑ ↓ ← → or W A S D move one square. Click the board first if the keys do nothing.</p>
        {finished && (
          result.completion ? (
            <div className="result ok">
              <b>Solved.</b> {result.completion.moves} moves in {result.completion.seconds} seconds, saved for {result.completion.player}.
              <button className="primary" onClick={onExit}>Back to the gallery</button>
            </div>
          ) : (
            <div className="result bad">
              <b>The server refused the run.</b> {result.message}
              <button className="primary" onClick={onExit}>Back to the gallery</button>
            </div>
          )
        )}
      </section>
    </>
  );
}

function PlayHeader({ maze, onExit }) {
  return (
    <header>
      <div>
        <p className="eyebrow">MAZEHUB / PLAY</p>
        <h1>{maze ? `${maze.width}×${maze.height} ${maze.difficulty}` : 'Play'}</h1>
        <p className="muted">{maze ? `by ${maze.author}` : 'Fetching the grid.'}</p>
      </div>
      <button className="ghost" onClick={onExit}>← Gallery</button>
    </header>
  );
}

/** The solution route may arrive as [[x,y],…] or [{x,y},…]. Accept both. */
function normalisePath(path) {
  if (!Array.isArray(path)) return [];
  return path.map((p) => (Array.isArray(p) ? { x: p[0], y: p[1] } : { x: p.x, y: p.y }));
}

const CELL_PIXELS = 26; // one maze cell on screen; 20x20 HARD then fits 520px
const WALL_PIXELS = 2;

function draw(canvas, maze, at, solution) {
  if (!canvas || !maze) return;
  const ratio = window.devicePixelRatio || 1;
  const w = maze.width * CELL_PIXELS;
  const h = maze.height * CELL_PIXELS;
  canvas.width = w * ratio;
  canvas.height = h * ratio;
  canvas.style.width = `${w}px`;
  canvas.style.height = `${h}px`;
  const ctx = canvas.getContext('2d');
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  const style = getComputedStyle(canvas);
  const colour = (name, fallback) => style.getPropertyValue(name).trim() || fallback;

  ctx.fillStyle = colour('--board', '#12161f');
  ctx.fillRect(0, 0, w, h);

  // Exit cell, so the goal is visible before the player reaches it.
  ctx.fillStyle = colour('--exit', '#3f8f6a');
  ctx.fillRect((maze.width - 1) * CELL_PIXELS + 3, (maze.height - 1) * CELL_PIXELS + 3, CELL_PIXELS - 6, CELL_PIXELS - 6);

  if (solution?.length) {
    ctx.strokeStyle = colour('--accent', '#e0a44c');
    ctx.lineWidth = 3;
    ctx.lineJoin = 'round';
    ctx.beginPath();
    solution.forEach((p, i) => {
      const cx = p.x * CELL_PIXELS + CELL_PIXELS / 2;
      const cy = p.y * CELL_PIXELS + CELL_PIXELS / 2;
      if (i === 0) ctx.moveTo(cx, cy); else ctx.lineTo(cx, cy);
    });
    ctx.stroke();
  }

  ctx.strokeStyle = colour('--wall', '#8d97ab');
  ctx.lineWidth = WALL_PIXELS;
  ctx.lineCap = 'square';
  ctx.beginPath();
  for (let y = 0; y < maze.height; y += 1) {
    for (let x = 0; x < maze.width; x += 1) {
      const walls = wallsOf(maze.grid[y][x]);
      const left = x * CELL_PIXELS;
      const top = y * CELL_PIXELS;
      const right = left + CELL_PIXELS;
      const bottom = top + CELL_PIXELS;
      if (walls.n) { ctx.moveTo(left, top); ctx.lineTo(right, top); }
      if (walls.e) { ctx.moveTo(right, top); ctx.lineTo(right, bottom); }
      if (walls.s) { ctx.moveTo(left, bottom); ctx.lineTo(right, bottom); }
      if (walls.w) { ctx.moveTo(left, top); ctx.lineTo(left, bottom); }
    }
  }
  ctx.stroke();

  ctx.fillStyle = colour('--player', '#f0c070');
  ctx.beginPath();
  ctx.arc(at.x * CELL_PIXELS + CELL_PIXELS / 2, at.y * CELL_PIXELS + CELL_PIXELS / 2, CELL_PIXELS / 2 - 6, 0, Math.PI * 2);
  ctx.fill();
}

function Publish({ author, onDone }) {
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const create = async (e) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    setBusy(true);
    setError('');
    try {
      await request('/mazes', jsonPost('POST', {
        title: f.get('title'), author: f.get('author'), difficulty: f.get('difficulty'),
      }));
      onDone();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <header>
        <div>
          <p className="eyebrow">MAZEHUB / PUBLISH</p>
          <h1>Publish a maze</h1>
          <p className="muted">The server carves the grid, checks it has a path and stores the shortest length.</p>
        </div>
        <button className="ghost" onClick={onDone}>← Gallery</button>
      </header>
      {error && <ErrorBanner message={error} />}
      <section className="panel form-panel">
        <form onSubmit={create}>
          <label>Title<input name="title" required maxLength={80} placeholder="e.g. Lantern Loop" /></label>
          <div className="form-row">
            <label>Author<input name="author" required defaultValue={author} maxLength={40} /></label>
            <label>Difficulty
              <select name="difficulty" defaultValue="EASY">
                {DIFFICULTIES.map((d) => <option key={d} value={d}>{d}</option>)}
              </select>
            </label>
          </div>
          <p className="muted">EASY is 8×8, MEDIUM is 14×14, HARD is 20×20.</p>
          <button className="primary full" disabled={busy}>{busy ? 'Generating…' : 'Publish'}</button>
        </form>
      </section>
    </>
  );
}

function Completed({ player }) {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(() => {
    setLoading(true);
    setError('');
    request(`/completions?player=${encodeURIComponent(player)}`)
      .then(setRows)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [player]);
  useEffect(() => { load(); }, [load]);

  const newestFirst = useMemo(
    () => [...rows].sort((a, b) => String(b.completed_at).localeCompare(String(a.completed_at))),
    [rows],
  );

  return (
    <>
      <header>
        <div>
          <p className="eyebrow">MAZEHUB / COMPLETED</p>
          <h1>Your solved mazes</h1>
          <p className="muted">Runs recorded for {player}, newest first.</p>
        </div>
        <button className="ghost" onClick={load}>↻ Refresh</button>
      </header>
      {error && <ErrorBanner message={error} onRetry={load} />}
      <section className="panel">
        {loading ? <div className="empty">Loading your runs…</div> : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Maze</th><th>Moves</th><th>Seconds</th><th>Completed</th></tr></thead>
              <tbody>
                {newestFirst.map((c) => (
                  <tr key={c.id}>
                    <td><b>{c.maze_title}</b></td>
                    <td>{c.moves}</td>
                    <td>{c.seconds}</td>
                    <td>{String(c.completed_at).replace('T', ' ').slice(0, 19)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!newestFirst.length && !error && <div className="empty">No runs yet. Solve a maze from the gallery.</div>}
          </div>
        )}
      </section>
    </>
  );
}

/** Which of the four edges of a cell a click landed nearest.
 *
 * Two steps on purpose: find the cell, then the nearest of its own four edges. A single
 * nearest-edge search over the whole grid would need every edge in a list and would still pick the
 * same one, so the cheap version wins.
 */
function edgeAt(px, py) {
  const x = Math.floor(px / CELL_PIXELS);
  const y = Math.floor(py / CELL_PIXELS);
  const inCellX = px - x * CELL_PIXELS;
  const inCellY = py - y * CELL_PIXELS;
  const distances = [
    { dir: 'N', away: inCellY },
    { dir: 'S', away: CELL_PIXELS - inCellY },
    { dir: 'W', away: inCellX },
    { dir: 'E', away: CELL_PIXELS - inCellX },
  ];
  const nearest = distances.reduce((best, one) => (one.away < best.away ? one : best));
  return { x, y, dir: nearest.dir };
}

function Draw({ author, onDone, onCancel }) {
  const [size, setSize] = useState(DRAW_SIZES[0]);
  const [grid, setGrid] = useState(() => closedGrid(DRAW_SIZES[0], DRAW_SIZES[0]));
  const [checked, setChecked] = useState(null); // the last local Check result
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const canvasRef = useRef(null);

  const resize = (next) => {
    setSize(next);
    setGrid(closedGrid(next, next));
    setChecked(null);
    setNotice('');
  };

  const clear = () => {
    setGrid(closedGrid(size, size));
    setChecked(null);
    setNotice('Every wall is closed again.');
  };

  // How many inner walls are open. Counted once per shared wall, from the east and south sides
  // only, so one opening is not counted twice.
  const openWalls = useMemo(() => {
    let open = 0;
    for (let y = 0; y < size; y += 1) {
      for (let x = 0; x < size; x += 1) {
        if (x + 1 < size && !(grid[y][x] & WALL_E)) open += 1;
        if (y + 1 < size && !(grid[y][x] & WALL_S)) open += 1;
      }
    }
    return open;
  }, [grid, size]);

  const onCanvasClick = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    // The canvas is drawn at devicePixelRatio but laid out at CSS pixels, so scale the hit test.
    const scale = (size * CELL_PIXELS) / rect.width;
    const spot = edgeAt((e.clientX - rect.left) * scale, (e.clientY - rect.top) * scale);
    if (spot.x < 0 || spot.y < 0 || spot.x >= size || spot.y >= size) return;
    if (isBorderEdge(size, size, spot.x, spot.y, spot.dir)) {
      setNotice('That is a border wall. The outside of the maze must stay closed.');
      return;
    }
    setGrid(toggleWall(grid, spot.x, spot.y, spot.dir));
    setChecked(null);
    setNotice('');
  };

  const check = () => {
    setChecked(solveLocal(grid));
    setNotice('');
  };

  const publish = async (e) => {
    e.preventDefault();
    const title = new FormData(e.currentTarget).get('title');
    const name = new FormData(e.currentTarget).get('author');
    setBusy(true);
    setError('');
    try {
      await request('/mazes/community', jsonPost('POST', {
        title, author: name, width: size, height: size, grid,
      }));
      onDone();
    } catch (err) {
      // The server runs the same five checks and answers 422 with the reason. Show its words.
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    draw(canvasRef.current, { width: size, height: size, grid }, { x: 0, y: 0 }, null);
  }, [grid, size]);

  return (
    <>
      <header>
        <div>
          <p className="eyebrow">MAZEHUB / DRAW</p>
          <h1>Draw a maze</h1>
          <p className="muted">Click near the edge of a cell to open or close that wall. Both sides move together.</p>
        </div>
        <button className="ghost" onClick={onCancel}>← Gallery</button>
      </header>
      {error && <ErrorBanner message={error} />}
      <section className="panel play-panel">
        <div className="panel-head">
          <div><h2>Canvas</h2><p className="muted">Every wall starts closed. The entrance is the dot, the exit is the green square.</p></div>
          <div className="card-actions">
            <div className="filters">
              {DRAW_SIZES.map((n) => (
                <button key={n} className={size === n ? 'selected' : ''} onClick={() => resize(n)}>{n}×{n}</button>
              ))}
            </div>
            <button className="ghost" onClick={clear}>Clear</button>
            <button className="primary" onClick={check}>Check</button>
          </div>
        </div>
        <div className="board">
          <canvas ref={canvasRef} onClick={onCanvasClick} style={{ cursor: 'crosshair' }} />
        </div>
        <section className="stats">
          <Stat label="size" value={`${size}×${size}`} />
          <Stat label="open walls" value={openWalls} />
          <Stat label="check" value={checked ? (checked.solvable ? 'solvable' : 'no path') : 'not run'} />
          <Stat label="path length" value={checked?.solvable ? checked.length : '—'} />
        </section>
        {notice && <p className="hint">{notice}</p>}
        {checked && (
          <div className={`result ${checked.solvable ? 'ok' : 'bad'}`}>
            {checked.solvable
              ? <span><b>Solvable.</b> The shortest path is {checked.length} cells, so {checked.length - 1} moves.</span>
              : <span><b>No path yet.</b> Open more walls between the top left and the bottom right.</span>}
          </div>
        )}
      </section>
      <section className="panel form-panel">
        <form onSubmit={publish}>
          <div className="form-row">
            <label>Title<input name="title" required maxLength={80} placeholder="e.g. Hand Cut" /></label>
            <label>Author<input name="author" required defaultValue={author} maxLength={40} /></label>
          </div>
          <p className="muted">The server repeats the check and derives the badge from the path length. Under 20 is EASY, 20 to 44 is MEDIUM, 45 and above is HARD.</p>
          <button className="primary full" disabled={busy || !checked?.solvable}>
            {busy ? 'Publishing…' : checked?.solvable ? 'Publish' : 'Run Check first'}
          </button>
        </form>
      </section>
    </>
  );
}

function Stat({ label, value }) {
  return (
    <div className="stat">
      <div className="stat-icon">▦</div>
      <div><small>{label}</small><strong>{typeof value === 'number' ? value : String(value)}</strong></div>
    </div>
  );
}

function ErrorBanner({ message, onRetry }) {
  return (
    <div className="alert">
      ⚠ {message}. The backend or PostgreSQL may be down.
      {onRetry && <button className="ghost" onClick={onRetry}>Try again</button>}
    </div>
  );
}

createRoot(document.getElementById('root')).render(<App />);
