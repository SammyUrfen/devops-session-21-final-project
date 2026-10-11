"""Add mazes.source and make mazes.seed nullable.

A hand-drawn maze has no seed: the grid itself is the only source of truth, so there is nothing to
reproduce it from. `source` keeps the drawn mazes out of the generated lists, which filter on it.

Existing rows are all generated and all carry a seed, so the new column takes a server default and
the seed column only loses its NOT NULL.
"""

import sqlalchemy as sa

from alembic import op

revision = "0002_add_maze_source"
down_revision = "0001_create_mazes"
branch_labels = None
depends_on = None

# Matches the Literal in app/schemas.py and the default on the model.
GENERATED = "GENERATED"


def upgrade():
    op.add_column(
        "mazes",
        sa.Column("source", sa.String(length=10), nullable=False, server_default=GENERATED),
    )
    op.alter_column("mazes", "seed", existing_type=sa.BigInteger(), nullable=True)


def downgrade():
    # A drawn maze cannot survive the downgrade, because it has no seed to put back.
    op.execute(f"DELETE FROM mazes WHERE source <> '{GENERATED}'")
    op.alter_column("mazes", "seed", existing_type=sa.BigInteger(), nullable=False)
    op.drop_column("mazes", "source")
