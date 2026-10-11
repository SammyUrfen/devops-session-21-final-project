"""Create the mazes and completions tables.

Single baseline migration. The earlier app's migration was dropped rather than kept in history,
because the two domains share no table and no deployment of MazeHub ever ran the old one.
"""

import sqlalchemy as sa

from alembic import op

revision = "0001_create_mazes"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "mazes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("author", sa.String(length=120), nullable=False, server_default="anonymous"),
        sa.Column("difficulty", sa.String(length=10), nullable=False, server_default="EASY"),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        # BigInteger: the seed comes from a 62-bit range, which overflows a 32-bit integer column.
        sa.Column("seed", sa.BigInteger(), nullable=False),
        sa.Column("grid", sa.Text(), nullable=False),
        sa.Column("solution_length", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "completions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "maze_id",
            sa.Integer(),
            sa.ForeignKey("mazes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("player", sa.String(length=120), nullable=False),
        sa.Column("moves", sa.Integer(), nullable=False),
        sa.Column("seconds", sa.Integer(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
    )
    # Every completion read filters or joins on maze_id, so the index is not optional.
    op.create_index("ix_completions_maze_id", "completions", ["maze_id"])


def downgrade():
    op.drop_index("ix_completions_maze_id", table_name="completions")
    op.drop_table("completions")
    op.drop_table("mazes")
