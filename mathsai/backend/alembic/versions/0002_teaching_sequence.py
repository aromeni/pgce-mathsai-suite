"""teaching sequence schema: year groups, versioned lesson content, AO tiers

Revision ID: 0002_teaching_sequence
Revises: 0001_initial_schema

Three changes, all driven by the content-quality pass:

1. `topics.year_group` — KS3 spans Years 7-9 and KS4 Years 10-11, far too
   wide to pitch generated content against. Seeded topics get a default.

2. `lesson_cache.content` + `schema_version` — the lesson is now a full
   teaching sequence (introduction, starter, I do, We do, adaptive teaching,
   plenary) rather than four flat fields, and it will keep evolving. Storing
   the validated document as JSON with a version stamp avoids a migration per
   pedagogical change. The version 1 columns are left in place and NOT
   dropped: they hold real generated content that is still usable, and
   discarding it would cost real money to replace.

3. `question_cache.difficulty` values renamed Foundation/Developing/Extending
   -> Fluency/Reasoning/Problem-solving. "Foundation" already meant Edexcel's
   tier of entry in `topics.difficulty_band`, so one word carried two
   different meanings in the same database. The new names follow Edexcel's
   Assessment Objectives and say what the pupil actually does.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_teaching_sequence"
down_revision: Union[str, Sequence[str], None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TIER_RENAMES = [
    ("Foundation", "Fluency"),
    ("Developing", "Reasoning"),
    ("Extending", "Problem-solving"),
]


def upgrade() -> None:
    op.add_column("topics", sa.Column("year_group", sa.Integer(), nullable=True))

    op.add_column("lesson_cache", sa.Column("content", sa.Text(), nullable=True))
    op.add_column(
        "lesson_cache",
        sa.Column(
            "schema_version", sa.Integer(), nullable=False, server_default="1"
        ),
    )

    # Existing rows predate `content`, so they are version 1 by definition.
    op.execute(
        "UPDATE lesson_cache SET schema_version = 1 WHERE content IS NULL"
    )

    for old, new in _TIER_RENAMES:
        op.execute(
            sa.text(
                "UPDATE question_cache SET difficulty = :new WHERE difficulty = :old"
            ).bindparams(new=new, old=old)
        )
        op.execute(
            sa.text(
                "UPDATE regeneration_log SET content_type = :new WHERE content_type = :old"
            ).bindparams(new=f"question:{new}", old=f"question:{old}")
        )


def downgrade() -> None:
    for old, new in _TIER_RENAMES:
        op.execute(
            sa.text(
                "UPDATE question_cache SET difficulty = :old WHERE difficulty = :new"
            ).bindparams(new=new, old=old)
        )
        op.execute(
            sa.text(
                "UPDATE regeneration_log SET content_type = :old WHERE content_type = :new"
            ).bindparams(new=f"question:{new}", old=f"question:{old}")
        )

    op.drop_column("lesson_cache", "schema_version")
    op.drop_column("lesson_cache", "content")
    op.drop_column("topics", "year_group")
