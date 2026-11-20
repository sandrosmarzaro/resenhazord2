"""add dev_admin to chat

Revision ID: 04501864102e
Revises: 21e07392eca2
Create Date: 2026-11-20 00:12:19.926878

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '04501864102e'
down_revision: Union[str, Sequence[str], None] = '21e07392eca2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # The server default fills existing chats with false, so no group changes behavior.
    op.add_column(
        'chat',
        sa.Column('dev_admin', sa.Boolean(), server_default=sa.false(), nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('chat', 'dev_admin')
