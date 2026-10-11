import sqlalchemy as sa
from alembic import op

revision = "0001_create_incidents"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "incidents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("service", sa.String(length=80), nullable=False, server_default="unknown"),
        sa.Column("severity", sa.String(length=10), nullable=False, server_default="SEV3"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="OPEN"),
        sa.Column("owner", sa.String(length=120), nullable=False, server_default="on-call"),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("incidents")
