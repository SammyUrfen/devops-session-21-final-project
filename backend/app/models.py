from datetime import UTC, datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _now() -> datetime:
    return datetime.now(UTC)


class Maze(Base):
    __tablename__ = "mazes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    author: Mapped[str] = mapped_column(String(120), default="anonymous")
    difficulty: Mapped[str] = mapped_column(String(10), default="EASY")
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    # GENERATED or COMMUNITY. The generated gallery filters on it, so a hand-drawn maze never
    # appears beside a carved one. See PLAN.md section 11.
    source: Mapped[str] = mapped_column(String(10), nullable=False, default="GENERATED")
    # BigInteger, not Integer: a seed is drawn from a 62-bit range so a published maze is hard to guess.
    # Nullable because a hand-drawn maze has no seed, its grid is the only source of truth.
    seed: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    # The wall bitmask grid as JSON text. Text keeps the column portable between Postgres and the
    # SQLite test database, and the grid is only ever read and written whole.
    grid: Mapped[str] = mapped_column(Text, nullable=False)
    # Shortest path length from the solver. The cheat guard compares a player's move count to it.
    solution_length: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    completions: Mapped[list["Completion"]] = relationship(
        back_populates="maze", cascade="all, delete-orphan", passive_deletes=True
    )


class Completion(Base):
    __tablename__ = "completions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # ondelete CASCADE: the database removes the runs of a deleted maze, so no orphan row survives
    # a delete that bypasses the ORM, for example a manual psql statement.
    maze_id: Mapped[int] = mapped_column(
        ForeignKey("mazes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    player: Mapped[str] = mapped_column(String(120), nullable=False)
    moves: Mapped[int] = mapped_column(Integer, nullable=False)
    seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    maze: Mapped[Maze] = relationship(back_populates="completions")
