"""add_performance_indexes

Revision ID: 472d7d3af394
Revises: c3f1a2b4d5e6
Create Date: 2026-06-15 16:49:33.434525

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '472d7d3af394'
down_revision: Union[str, Sequence[str], None] = 'c3f1a2b4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Indexes for matches table
    op.create_index('ix_matches_game_type', 'matches', ['game_type'], unique=False)
    op.create_index('ix_matches_status', 'matches', ['status'], unique=False)
    
    # Indexes for decision_logs table
    op.create_index('ix_decision_logs_agent_id', 'decision_logs', ['agent_id'], unique=False)
    op.create_index('ix_decision_logs_match_id', 'decision_logs', ['match_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_decision_logs_match_id', table_name='decision_logs')
    op.drop_index('ix_decision_logs_agent_id', table_name='decision_logs')
    op.drop_index('ix_matches_status', table_name='matches')
    op.drop_index('ix_matches_game_type', table_name='matches')
