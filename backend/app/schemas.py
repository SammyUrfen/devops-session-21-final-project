from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Difficulty = Literal["EASY", "MEDIUM", "HARD"]


class MazeCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    author: str = Field(default="anonymous", min_length=1, max_length=120)
    difficulty: Difficulty = "EASY"


class MazeUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    difficulty: Difficulty | None = None


class MazeOut(BaseModel):
    id: int
    title: str
    author: str
    difficulty: Difficulty
    width: int
    height: int
    seed: int
    # One row for each y, one wall bitmask for each x. See app/maze.py for the bit convention.
    grid: list[list[int]]
    solution_length: int
    created_at: datetime
    completion_count: int


class CompletionCreate(BaseModel):
    player: str = Field(min_length=1, max_length=120)
    moves: int = Field(ge=1)
    seconds: int = Field(ge=0)


class CompletionOut(BaseModel):
    id: int
    maze_id: int
    maze_title: str
    player: str
    moves: int
    seconds: int
    completed_at: datetime


class SolutionOut(BaseModel):
    path: list[tuple[int, int]]
    length: int


class StatsOut(BaseModel):
    total: int
    by_difficulty: dict[str, int]
    completions: int
    authors: int
