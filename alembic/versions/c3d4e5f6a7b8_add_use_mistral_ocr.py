"""add_use_mistral_ocr_to_dietary_profiles

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-03-22 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'dietary_profiles',
        sa.Column('use_mistral_ocr', sa.Boolean(), nullable=True, server_default=sa.text('false')),
    )
    op.execute("UPDATE dietary_profiles SET use_mistral_ocr = false WHERE use_mistral_ocr IS NULL")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('dietary_profiles', 'use_mistral_ocr')
