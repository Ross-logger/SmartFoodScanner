"""add_use_hf_section_detection_to_dietary_profiles

Revision ID: a1b2c3d4e5f6
Revises: 886b257bad8e
Create Date: 2026-03-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '886b257bad8e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'dietary_profiles',
        sa.Column('use_hf_section_detection', sa.Boolean(), nullable=True, server_default=sa.text('false')),
    )
    op.execute("UPDATE dietary_profiles SET use_hf_section_detection = false WHERE use_hf_section_detection IS NULL")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('dietary_profiles', 'use_hf_section_detection')
