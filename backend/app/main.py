import json
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, status
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import event, func, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from . import maze as maze_lib
from .config import settings
from .db import Base, engine, get_db
from .models import Completion, Maze
from .schemas import (
    CompletionCreate,
    CompletionOut,
    MazeCreate,
    MazeOut,
    MazeUpdate,
    SolutionOut,
    StatsOut,
)


@event.listens_for(Engine, "connect")
def _enforce_sqlite_foreign_keys(dbapi_connection, _record) -> None:
    """SQLite ignores a foreign key unless each connection asks for it, Postgres always honours it.

    Without this the cascade delete would pass on Postgres and leave orphan rows in the tests.
    """
    if engine.dialect.name != "sqlite":
        return
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Containers run `alembic upgrade head` first, so this is a no-op there. It keeps tests self-contained.
    Base.metadata.create_all(bind=engine)
    yield


# One alias for the request-scoped session, so every route reads the same way.
DbSession = Annotated[Session, Depends(get_db)]

app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
Instrumentator().instrument(app).expose(app, endpoint="/metrics")


def _to_out(maze: Maze) -> MazeOut:
    return MazeOut(
        id=maze.id,
        title=maze.title,
        author=maze.author,
        difficulty=maze.difficulty,
        width=maze.width,
        height=maze.height,
        seed=maze.seed,
        grid=json.loads(maze.grid),
        solution_length=maze.solution_length,
        created_at=maze.created_at,
        completion_count=len(maze.completions),
    )


def _get_or_404(db: Session, maze_id: int) -> Maze:
    maze = db.get(Maze, maze_id)
    if maze is None:
        raise HTTPException(status_code=404, detail="Maze not found")
    return maze


def _carve(maze: Maze, difficulty: str, seed: int) -> None:
    """Fill the size, seed, grid and solution length of a maze from its difficulty.

    Used on publish and again when an edit changes the difficulty, because a new difficulty means a
    new grid size, so the old grid cannot be kept.
    """
    width, height = maze_lib.SIZES[difficulty]
    grid, path = maze_lib.generate_verified(width, height, seed)
    maze.difficulty = difficulty
    maze.width = width
    maze.height = height
    maze.seed = seed
    maze.grid = json.dumps(grid)
    maze.solution_length = len(path)


@app.get("/")
def root():
    return {"service": settings.app_name, "environment": settings.environment, "docs": "/docs"}


@app.get("/health")
def health():
    """Liveness: the process answers. No DB call, so a DB outage does not restart every pod."""
    return {"status": "UP"}


@app.get("/ready")
def ready(db: DbSession):
    """Readiness: the DB answers. A failing DB takes the pod out of the Service, it does not kill it."""
    db.execute(text("SELECT 1"))
    return {"status": "READY"}


@app.get("/api/config")
def config():
    return {"environment": settings.environment, "banner": settings.banner}


@app.get("/api/mazes", response_model=list[MazeOut])
def list_mazes(
    db: DbSession,
    difficulty: str | None = Query(default=None),
    author: str | None = Query(default=None),
):
    query = select(Maze).order_by(Maze.id.desc())
    if difficulty:
        query = query.where(Maze.difficulty == difficulty)
    if author:
        query = query.where(Maze.author == author)
    return [_to_out(m) for m in db.scalars(query)]


# Declared before /api/mazes/{maze_id}: FastAPI matches in declaration order, so the other way round
# "stats" would be parsed as a maze id and fail.
@app.get("/api/mazes/stats", response_model=StatsOut)
def stats(db: DbSession):
    counts = dict(
        db.execute(select(Maze.difficulty, func.count(Maze.id)).group_by(Maze.difficulty)).all()
    )
    return StatsOut(
        total=sum(counts.values()),
        by_difficulty={key: counts.get(key, 0) for key in maze_lib.SIZES},
        completions=db.scalar(select(func.count(Completion.id))) or 0,
        authors=db.scalar(select(func.count(func.distinct(Maze.author)))) or 0,
    )


@app.get("/api/mazes/{maze_id}", response_model=MazeOut)
def get_maze(maze_id: int, db: DbSession):
    return _to_out(_get_or_404(db, maze_id))


@app.post("/api/mazes", response_model=MazeOut, status_code=status.HTTP_201_CREATED)
def create_maze(payload: MazeCreate, db: DbSession):
    """The server picks the seed and verifies the grid. A client never supplies either."""
    maze = Maze(title=payload.title, author=payload.author)
    _carve(maze, payload.difficulty, maze_lib.new_seed())
    db.add(maze)
    db.commit()
    db.refresh(maze)
    return _to_out(maze)


@app.put("/api/mazes/{maze_id}", response_model=MazeOut)
def update_maze(maze_id: int, payload: MazeUpdate, db: DbSession):
    maze = _get_or_404(db, maze_id)
    fields = payload.model_dump(exclude_unset=True)
    if fields.get("title"):
        maze.title = fields["title"]
    new_difficulty = fields.get("difficulty")
    if new_difficulty and new_difficulty != maze.difficulty:
        _carve(maze, new_difficulty, maze_lib.new_seed())
    db.commit()
    db.refresh(maze)
    return _to_out(maze)


@app.delete("/api/mazes/{maze_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_maze(maze_id: int, db: DbSession):
    db.delete(_get_or_404(db, maze_id))
    db.commit()


@app.get("/api/mazes/{maze_id}/solution", response_model=SolutionOut)
def get_solution(maze_id: int, db: DbSession):
    """Solve on demand instead of storing the path: the grid is the source of truth, and the solver
    runs in well under a millisecond at these sizes."""
    maze = _get_or_404(db, maze_id)
    path = maze_lib.solve(json.loads(maze.grid))
    return SolutionOut(path=path, length=len(path))


@app.post(
    "/api/mazes/{maze_id}/completions",
    response_model=CompletionOut,
    status_code=status.HTTP_201_CREATED,
)
def create_completion(maze_id: int, payload: CompletionCreate, db: DbSession):
    """Record a solved run.

    Cheat guard: a real run cannot take fewer moves than the shortest path, because every move
    crosses one open wall and the solver already found the minimum. A lower count means the client
    posted a made-up score, so reject it with 422 rather than store a leaderboard nobody trusts.
    More moves than the minimum are normal, the player wandered.
    """
    maze = _get_or_404(db, maze_id)
    if payload.moves < maze.solution_length:
        raise HTTPException(
            status_code=422,
            detail=(
                f"{payload.moves} moves is below the shortest path of "
                f"{maze.solution_length} cells, so the run is not possible"
            ),
        )
    done = Completion(maze_id=maze.id, **payload.model_dump())
    db.add(done)
    db.commit()
    db.refresh(done)
    return CompletionOut(**{k: getattr(done, k) for k in
                            ("id", "maze_id", "player", "moves", "seconds", "completed_at")},
                         maze_title=maze.title)


@app.get("/api/completions", response_model=list[CompletionOut])
def list_completions(db: DbSession, player: str | None = Query(default=None)):
    query = (
        select(Completion, Maze.title)
        .join(Maze, Maze.id == Completion.maze_id)
        .order_by(Completion.id.desc())
    )
    if player:
        query = query.where(Completion.player == player)
    return [
        CompletionOut(
            id=done.id,
            maze_id=done.maze_id,
            maze_title=title,
            player=done.player,
            moves=done.moves,
            seconds=done.seconds,
            completed_at=done.completed_at,
        )
        for done, title in db.execute(query).all()
    ]
