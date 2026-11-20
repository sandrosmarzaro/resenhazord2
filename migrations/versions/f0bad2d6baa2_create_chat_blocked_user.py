"""create chat_blocked_user

Revision ID: f0bad2d6baa2
Revises: 04501864102e
Create Date: 2026-11-20 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f0bad2d6baa2'
down_revision: Union[str, Sequence[str], None] = '04501864102e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # alt_key holds the member's other WhatsApp identity (LID or PN), so a block set
    # through either form matches a sender that arrives in the other.
    op.create_table(
        'chat_blocked_user',
        sa.Column('chat_id', sa.Uuid(), nullable=False),
        sa.Column('user_key', sa.String(length=64), nullable=False),
        sa.Column('alt_key', sa.String(length=64), nullable=True),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['chat_id'], ['chat.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('chat_id', 'user_key', name='uq_blocked_chat_user'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('chat_blocked_user')
