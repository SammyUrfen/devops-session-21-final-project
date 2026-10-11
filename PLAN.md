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
