# Capstone plan — MazeHub

Session 21 final capstone. The rubric of record is `devops-heros/session21-python/GRADING.md`, 100 points
across 10 modules. This plan replaces the IncidentBoard app with MazeHub and keeps the DevOps layer.

**Deadline.** 16 October 2026. Confirmed on 12 October.

---

## 1. Decisions

| Decision | Choice |
|---|---|
| Application | MazeHub. A maze gallery in the style of maze.toys. |
| Sign in | None. The player types a name, and the browser stores it. |
| Kubernetes evidence | minikube for Modules 8 and 9. EKS for Module 7, in one timed window. |
| Screenshots | You take them. I keep each service running and give you a capture list. |
| Repository layout | The rubric layout. See section 2. |

**Layout conflict.** The homework file asks for `application/`, `docker/`, `kubernetes/`. The rubric asks
for `backend/`, `frontend/`, `docker-compose.yml` at the root, and `k8s/`. The rubric carries the points,
so the rubric wins. The README records the mapping.

---

## 2. Target layout

```text
devops-session-21-final-project/
├── backend/            app/ tests/ alembic/ Dockerfile requirements.txt pytest.ini
├── frontend/           src/ index.html Dockerfile nginx.conf package.json
├── docker-compose.yml  frontend + backend + postgres
├── k8s/                namespace.yaml, troubleshooting/
├── helm/mazehub/       Chart.yaml values.yaml templates/
├── terraform/          VPC + 2 public subnets + EKS + ECR
├── monitoring/         kube-prometheus-stack values, Grafana dashboard
├── gitops/             Argo CD Application
├── security/           gitleaks.toml, .trivyignore
├── scripts/            load-test.sh, demo runsheet
└── .github/workflows/  ci-cd.yml
```

---

## 3. The application

### Why this app answers the plagiarism rule

The course app is one table of tasks. MazeHub has two tables with a foreign key, a generated artifact and
a verified invariant. The maze generator and the solver are written from scratch.

### Data model (Alembic migration `0001_create_mazes`)

| Table | Columns |
|---|---|
| `mazes` | id, title, author, difficulty, width, height, seed, grid, solution_length, created_at |
| `completions` | id, maze_id (FK, cascade delete), player, moves, seconds, completed_at |

`grid` holds one wall bitmask for each cell, as JSON text. `seed` makes the grid reproducible.

### Primitives written from scratch (`backend/app/maze.py`)

1. **Generator.** Randomized depth-first carving on a grid, with a seeded random source.
2. **Solver.** Breadth-first search from the entrance to the exit. It gives `solution_length`.
3. **Invariant guard.** The generator rejects a grid when the solver finds no path.

Difficulty sets the size: EASY 8x8, MEDIUM 14x14, HARD 20x20.

### API

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness. No database read. |
| GET | `/ready` | Readiness. Reads the database. |
| GET | `/metrics` | Prometheus format. |
| GET | `/api/mazes` | List. Filters: `difficulty`, `author`. |
| GET | `/api/mazes/{id}` | One maze with its grid. |
| POST | `/api/mazes` | Publish. The server generates and verifies the grid. |
| PUT | `/api/mazes/{id}` | Edit the title or the difficulty. |
| DELETE | `/api/mazes/{id}` | Remove the maze and its completions. |
| GET | `/api/mazes/stats` | Counts for each difficulty, and the completion total. |
| GET | `/api/mazes/{id}/solution` | The shortest path. The "show me" button uses it. |
| POST | `/api/mazes/{id}/completions` | Record a solved run: player, moves, seconds. |
| GET | `/api/completions` | Completed mazes. Filter: `player`. |

### Frontend (React, Vite, canvas)

- Gallery: KPI cards, difficulty filter, maze cards.
- Play view: the canvas draws the maze. Arrow keys and WASD move. A timer and a move counter run.
- On the exit cell, the browser posts a completion.
- Publish form: title, author, difficulty.
- Completed view: the completions of the stored player name.

### Tests (12, pytest, SQLite test database)

Generator: every cell is reachable, the same seed gives the same grid, the solver length is correct.
API: health, ready, list, create, read, update, delete, stats, completion flow.

---

## 4. Rename sweep

`incidentboard` to `mazehub` in 17 files: the Helm chart directory and templates, `values.yaml`,
the compose file, the CI workflow, the Argo CD files, the namespace, the Grafana dashboard,
`package.json` and the Terraform variables. The GHCR image names change to `mazehub-backend`
and `mazehub-frontend`.

---

## 5. Terraform change (Module 7, 15 points)

The current code gives 1 public subnet, an EC2 instance and an ECR repository. The rubric wants two
public subnets and an EKS cluster with a worker node group.

| Change | Reason |
|---|---|
| Two public subnets in two availability zones | Rubric, 3 points. EKS also needs two zones. |
| EKS module 20.x, Kubernetes 1.31, one managed node group | Rubric, 4 points |
| Private subnets and one NAT gateway | The node group needs outbound access |
| Keep the ECR repository | The pipeline can push there as well as to GHCR |
| Drop the EC2 instance | EKS replaces it. It only adds cost. |

**You must do this first.** The AWS user needs more rights. EKS creation calls `iam:CreateRole`,
`iam:AttachRolePolicy`, `iam:PassRole`, `eks:*` and `logs:*`. Attach `AdministratorAccess` to
`SammyUrfen-CLI` for the window, then remove it.

**Cost and time.** The control plane, two t3.medium nodes and one NAT gateway cost about USD 0.25 each
hour. Creation takes about 15 minutes. Destruction takes about 15 minutes. Budget USD 0.30 to 0.60.

---

## 6. Module coverage

| Module | Points | State now | Work left |
|---|---|---|---|
| M1 App | 10 | IncidentBoard, one table | Build MazeHub |
| M2 Tests | 10 | 8 tests pass | 12 tests for the new domain |
| M3 Git | 5 | 4 commits | The rubric wants 10. The phases below add them. |
| M4 Docker | 10 | Both images build, non-root, multi-stage | Move the files, rename |
| M5 CI/CD | 15 | Pipeline green | Confirm the SHA tag and both images |
| M6 Trivy | 5 | Scan and gate run | Write the CVE explanation |
| M7 Terraform | 15 | No EKS | Section 5 |
| M8 Kubernetes and Helm | 15 | Ran on minikube | Rename, run again, capture |
| M9 Monitoring | 10 | Prometheus, Grafana, alert ran | Add a MazeHub panel, capture |
| M10 Docs | 5 | README is a stub | Full README and a demo runsheet |

---

## 7. Phases

| Phase | Work | Time |
|---|---|---|
| P1 | Restructure and rename to the target layout | 30 min |
| P2 | Backend: model, migration, generator, solver, API, tests | 60 min |
| P3 | Frontend: gallery, canvas play view, publish, completed | 60 min |
| P4 | Local stack: compose up, pytest, minikube, Helm, monitoring | 45 min |
| P5 | Pipeline green, GHCR images with SHA tags, Trivy note | 30 min |
| P6 | Terraform EKS: plan, apply, your screenshots, destroy | 75 min |
| P7 | README, troubleshooting cases, demo runsheet | 45 min |

Total: about 5.5 hours of work.

---

## 8. Your capture list

I keep each service running and tell you when to capture. The browser items run on localhost.

1. The app in the browser, through compose on port 3000.
2. `pytest -v`, all tests pass.
3. `docker compose up --build`, the three services start.
4. The GitHub Actions run, green.
5. The GHCR package page, with the commit SHA tag.
6. The Trivy step output.
7. `terraform plan` output.
8. The AWS console, the VPC and the EKS cluster. Only you can take this one.
9. `terraform destroy` output.
10. `kubectl get pods`, `kubectl get svc`, `helm list`.
11. The app through the Ingress host.
12. The `/metrics` output, the Prometheus targets page, the Grafana panel.
13. The commit history, 10 commits or more.

---

## 9. Risks

| Risk | Control |
|---|---|
| EKS creation fails on rights | Attach `AdministratorAccess` before the window. Check with `aws sts get-caller-identity`. |
| EKS resources stay and cost money | `destroy` runs in the same session. I check the console API after it. |
| The maze canvas does not work in the browser | A keyboard-free fallback: the solution path draws on request. |
| The session hits a usage limit | Each phase ends with a commit. Work resumes from the last commit. |

---

## 10. API contract (frozen, backend worker)

The backend is built. The frontend and the Helm chart build against the names below. Do not rename a
field or a path without a note in this section.

### Difficulty and size

| Difficulty | Width | Height |
|---|---|---|
| `EASY` | 8 | 8 |
| `MEDIUM` | 14 | 14 |
| `HARD` | 20 | 20 |

Any other value returns 422. The size map lives in `SIZES` in `backend/app/maze.py`.

### Maze JSON

```json
{
  "id": 1,
  "title": "Hedge",
  "author": "anonymous",
  "difficulty": "MEDIUM",
  "width": 14,
  "height": 14,
  "seed": 3821993271084116,
  "grid": [[11, 13, 3], [12, 5, 6]],
  "solution_length": 41,
  "created_at": "2026-10-12T09:14:02.511Z",
  "completion_count": 0
}
```

The `grid` above is shortened to a real 3x2 carve, so the example fits on the page. A real MEDIUM
maze holds 14 rows of 14 integers.

`grid` holds `height` rows. Each row holds `width` integers, indexed `grid[y][x]`. One integer is the
wall bitmask of one cell. A set bit means a wall is present.

| Bit | Value | Side | Neighbour |
|---|---|---|---|
| N | 1 | top | `y - 1` |
| E | 2 | right | `x + 1` |
| S | 4 | bottom | `y + 1` |
| W | 8 | left | `x - 1` |

A closed cell is 15. The entrance is `(0, 0)`. The exit is `(width - 1, height - 1)`. The two cells on
each side of a wall always agree, so the renderer can draw every edge of every cell and get a clean
grid. `solution_length` counts cells on the shortest path, so it includes the entrance and the exit.
The smallest possible move count is `solution_length - 1`.

### Completion JSON

```json
{
  "id": 7,
  "maze_id": 1,
  "maze_title": "Hedge",
  "player": "nova",
  "moves": 58,
  "seconds": 42,
  "completed_at": "2026-10-12T09:20:44.102Z"
}
```

### Routes

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/` | — | Service name, environment, docs path |
| GET | `/health` | — | `{"status": "UP"}`. No database read. |
| GET | `/ready` | — | `{"status": "READY"}`. Reads the database. |
| GET | `/metrics` | — | Prometheus text format |
| GET | `/api/config` | — | `{environment, banner}` |
| GET | `/api/mazes` | — | List of Maze, newest first. Query: `difficulty`, `author`. |
| GET | `/api/mazes/stats` | — | `{total, by_difficulty: {EASY, MEDIUM, HARD}, completions, authors}` |
| GET | `/api/mazes/{id}` | — | Maze. 404 when missing. |
| POST | `/api/mazes` | `{title, author?, difficulty}` | 201 Maze |
| PUT | `/api/mazes/{id}` | `{title?, difficulty?}` | Maze. 404 when missing. |
| DELETE | `/api/mazes/{id}` | — | 204. 404 when missing. |
| GET | `/api/mazes/{id}/solution` | — | `{path: [[x, y], ...], length}` |
| POST | `/api/mazes/{id}/completions` | `{player, moves, seconds}` | 201 Completion |
| GET | `/api/completions` | — | List of Completion, newest first. Query: `player`. |

### Rules the frontend must respect

1. The server picks the seed. A client never sends `seed`, `width`, `height`, `grid` or
   `solution_length`. The server generates the grid and verifies it before it stores it.
2. A `difficulty` change on `PUT` regenerates the grid at the new size, with a new seed. The old grid
   is gone. A `title`-only `PUT` leaves the grid untouched.
3. `DELETE` removes the completions of that maze as well, through a cascade in the database.
4. `POST /api/mazes/{id}/completions` rejects a `moves` value below `solution_length` with 422 and a
   message that names both numbers. This is the cheat guard. Send the real move count.
5. `/api/mazes/stats` is declared before `/api/mazes/{id}`, because FastAPI matches paths in
   declaration order. Keep that order.
6. `/api/mazes` includes the full `grid` for each maze. A HARD gallery page is therefore a few hundred
   kilobytes. That is accepted for a 20x20 grid and a small gallery.

---

## 11. Community mazes, drawn by hand (contract change, 12 October)

The user asked for an interactive drawer. A person draws the walls. The server never generates that
grid. Drawn mazes stay out of the EASY, MEDIUM and HARD lists. They live in their own list.

### Model change

| Change | Detail |
|---|---|
| New column `mazes.source` | `GENERATED` or `COMMUNITY`. Default `GENERATED`. Not null. |
| `mazes.seed` becomes nullable | A drawn maze has no seed. The grid is the only source of truth. |
| `mazes.difficulty` for a drawn maze | The server derives it from the path length. See the table below. |
| Migration | A second migration, `0002_add_maze_source`. Keep `0001` as it is. |

Derived label for a drawn maze, from `solution_length`:

| Path length | Label |
|---|---|
| under 20 | `EASY` |
| 20 to 44 | `MEDIUM` |
| 45 and above | `HARD` |

The label is a badge only. The generated lists filter on `source=GENERATED`, so a drawn maze never
appears beside a generated one.

### New and changed routes

| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/api/mazes/community` | `{title, author?, width, height, grid}` | 201 Maze with `source=COMMUNITY` |
| GET | `/api/mazes` | — | Gains the query `source=GENERATED\|COMMUNITY`. No value means both. |
| GET | `/api/mazes/stats` | — | Gains `by_source: {GENERATED, COMMUNITY}` |

`PUT /api/mazes/{id}` on a drawn maze changes the title only. A `difficulty` value returns 422,
because the server must not replace a grid that a person drew.

### The structural guard (server side, 422 with a named reason)

A drawn grid is rejected unless every check passes. Each check returns its own message.

1. `width` and `height` are between 4 and 20, and the grid matches them exactly.
2. Every value is an integer from 0 to 15.
3. The outer border is closed: the top row has the N bit, the bottom row the S bit, and so for E and W.
4. Neighbours agree: the E bit of `(x, y)` equals the W bit of `(x + 1, y)`. The same holds for N and S.
5. A path exists from `(0, 0)` to `(width - 1, height - 1)`. The breadth-first search proves it and
   gives `solution_length`.

Check 4 is the one a drawing tool breaks most often. The client keeps both sides in step, and the
server never trusts it.

### Frontend

- A new "Draw" view. A canvas shows a grid of cells, every wall closed at the start.
- A click near a cell edge toggles that wall. The tool toggles the neighbour side as well, so check 4
  always passes.
- A size control: 8x8, 12x12 or 16x16.
- A "Check" button runs the same breadth-first search in the browser and reports solvable or not, with
  the path length. The check is local, so it is instant. The server repeats it anyway.
- "Clear" closes every wall again. "Publish" sends the grid.
- The gallery gets two tabs: "Generated" and "Community". The difficulty chips apply to the first tab.

### Tests to add

Backend, each one its own case: a good drawn maze is accepted, a wall that two cells disagree on is
rejected, an open border is rejected, an unsolvable grid is rejected, a value above 15 is rejected,
a size outside the range is rejected, the derived label matches the path length, and `PUT` with a
difficulty on a drawn maze returns 422.

Frontend `node --test`: a toggle changes both sides of the wall, a toggle twice returns the start
state, and the local search agrees with a known small grid.

### No personal name in the app

The app shows no personal name. The player-name field uses a neutral placeholder. The author field
defaults to the stored player name, or to `anonymous`. The GHCR image path keeps the account name
`sammyurfen`, because that is the registry namespace, not app text.
