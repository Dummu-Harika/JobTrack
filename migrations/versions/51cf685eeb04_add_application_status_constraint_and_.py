
"""Align existing JobTrack database schema with models."""

from alembic import op
import sqlalchemy as sa

revision = "51cf685eeb04"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Update users table.
    op.alter_column(
        "users", "name",
        existing_type=sa.String(100),
        type_=sa.String(120),
        existing_nullable=False,
    )
    op.alter_column(
        "users", "email",
        existing_type=sa.String(120),
        type_=sa.String(254),
        existing_nullable=False,
    )
    op.alter_column(
        "users", "created_at",
        existing_type=sa.DateTime(),
        nullable=False,
        existing_nullable=True,
    )

    # Update applications table.
    op.alter_column(
        "applications", "location",
        existing_type=sa.String(150),
        type_=sa.String(200),
        existing_nullable=True,
    )
    op.alter_column(
        "applications", "job_url",
        existing_type=sa.String(500),
        type_=sa.String(2048),
        existing_nullable=True,
    )
    op.alter_column(
        "applications", "status",
        existing_type=sa.String(50),
        nullable=False,
        existing_nullable=True,
    )
    op.alter_column(
        "applications", "created_at",
        existing_type=sa.DateTime(),
        nullable=False,
        existing_nullable=True,
    )
    op.alter_column(
        "applications", "updated_at",
        existing_type=sa.DateTime(),
        nullable=False,
        existing_nullable=True,
    )

    # Add indexes missing from the existing database.
    op.create_index(
        "ix_applications_user_id",
        "applications",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_applications_user_status",
        "applications",
        ["user_id", "status"],
        unique=False,
    )

    # Restrict application status to valid values.
    op.create_check_constraint(
        "check_application_status",
        "applications",
        "status IN ('Applied', 'Assessment', 'Interview', 'Offer', 'Rejected')",
    )


def downgrade():
    op.drop_constraint(
        "check_application_status",
        "applications",
        type_="check",
    )
    op.drop_index(
        "ix_applications_user_status",
        table_name="applications",
    )
    op.drop_index(
        "ix_applications_user_id",
        table_name="applications",
    )

    op.alter_column(
        "applications", "updated_at",
        existing_type=sa.DateTime(),
        nullable=True,
        existing_nullable=False,
    )
    op.alter_column(
        "applications", "created_at",
        existing_type=sa.DateTime(),
        nullable=True,
        existing_nullable=False,
    )
    op.alter_column(
        "applications", "status",
        existing_type=sa.String(50),
        nullable=True,
        existing_nullable=False,
    )
    op.alter_column(
        "applications", "job_url",
        existing_type=sa.String(2048),
        type_=sa.String(500),
        existing_nullable=True,
    )
    op.alter_column(
        "applications", "location",
        existing_type=sa.String(200),
        type_=sa.String(150),
        existing_nullable=True,
    )

    op.alter_column(
        "users", "created_at",
        existing_type=sa.DateTime(),
        nullable=True,
        existing_nullable=False,
    )
    op.alter_column(
        "users", "email",
        existing_type=sa.String(254),
        type_=sa.String(120),
        existing_nullable=False,
    )
    op.alter_column(
        "users", "name",
        existing_type=sa.String(120),
        type_=sa.String(100),
        existing_nullable=False,
    )
