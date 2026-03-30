"""consolidate_use_llm_dietary_profile

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-03-30 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "dietary_profiles",
        sa.Column(
            "use_llm",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    bind = op.get_bind()
    # Preserve prior behaviour: either old flag enabled -> use_llm on
    if bind.dialect.name == "postgresql":
        bind.execute(
            sa.text(
                "UPDATE dietary_profiles SET use_llm = true WHERE "
                "COALESCE(use_llm_ingredient_extractor, false) IS true "
                "OR COALESCE(use_mistral_ocr, false) IS true"
            )
        )
    else:
        bind.execute(
            sa.text(
                "UPDATE dietary_profiles SET use_llm = 1 WHERE "
                "COALESCE(use_llm_ingredient_extractor, 0) = 1 "
                "OR COALESCE(use_mistral_ocr, 0) = 1"
            )
        )
    op.drop_column("dietary_profiles", "use_llm_ingredient_extractor")
    op.drop_column("dietary_profiles", "use_mistral_ocr")
    op.alter_column(
        "dietary_profiles",
        "use_llm",
        server_default=None,
    )


def downgrade() -> None:
    op.add_column(
        "dietary_profiles",
        sa.Column(
            "use_llm_ingredient_extractor",
            sa.Boolean(),
            nullable=True,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "dietary_profiles",
        sa.Column(
            "use_mistral_ocr",
            sa.Boolean(),
            nullable=True,
            server_default=sa.false(),
        ),
    )
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "UPDATE dietary_profiles SET use_llm_ingredient_extractor = use_llm, "
            "use_mistral_ocr = use_llm"
        )
    )
    op.drop_column("dietary_profiles", "use_llm")
