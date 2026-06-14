"""Add performance indexes for matches and decision_logs

Revision ID: f9a2e3c1b4d7
Revises: c3f1a2b4d5e6
Create Date: 2026-06-14 12:00:00.000000

Indexes added:
  - matches: game_type, mode, started_at (bulk simulation and leaderboard queries)
  - match_participants: match_id, player_id, agent_id (join-heavy queries)
  - decision_logs: agent_id, match_id, logged_at (developer analytics bulk reads)
  - agents: owner_id, status (fleet hub and matchmaking queries)
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f9a2e3c1b4d7'
down_revision = 'c3f1a2b4d5e6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # matches — game_type filter used by leaderboard and simulation endpoints
    op.create_index('ix_matches_game_type', 'matches', ['game_type'], unique=False)
    # matches — mode filter (live vs bulk) used by simulation reports
    op.create_index('ix_matches_mode', 'matches', ['mode'], unique=False)
    # matches — started_at used for ordered history queries
    op.create_index('ix_matches_started_at', 'matches', ['started_at'], unique=False)

    # match_participants — queried by match_id on every turn to resolve seat data
    op.create_index('ix_match_participants_match_id', 'match_participants', ['match_id'], unique=False)
    # match_participants — queried by player_id for match history page
    op.create_index('ix_match_participants_player_id', 'match_participants', ['player_id'], unique=False)
    # match_participants — queried by agent_id for developer analytics
    op.create_index('ix_match_participants_agent_id', 'match_participants', ['agent_id'], unique=False)

    # decision_logs — bulk read by agent_id (developer analytics, log download)
    op.create_index('ix_decision_logs_agent_id', 'decision_logs', ['agent_id'], unique=False)
    # decision_logs — queried by match_id when viewing a specific match log
    op.create_index('ix_decision_logs_match_id', 'decision_logs', ['match_id'], unique=False)
    # decision_logs — ordered by logged_at for chronological display
    op.create_index('ix_decision_logs_logged_at', 'decision_logs', ['logged_at'], unique=False)

    # agents — queried by owner_id for fleet hub and agent manager pages
    op.create_index('ix_agents_owner_id', 'agents', ['owner_id'], unique=False)
    # agents — filtered by status (active/paused/banned) for matchmaking
    op.create_index('ix_agents_status', 'agents', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_agents_status', table_name='agents')
    op.drop_index('ix_agents_owner_id', table_name='agents')
    op.drop_index('ix_decision_logs_logged_at', table_name='decision_logs')
    op.drop_index('ix_decision_logs_match_id', table_name='decision_logs')
    op.drop_index('ix_decision_logs_agent_id', table_name='decision_logs')
    op.drop_index('ix_match_participants_agent_id', table_name='match_participants')
    op.drop_index('ix_match_participants_player_id', table_name='match_participants')
    op.drop_index('ix_match_participants_match_id', table_name='match_participants')
    op.drop_index('ix_matches_started_at', table_name='matches')
    op.drop_index('ix_matches_mode', table_name='matches')
    op.drop_index('ix_matches_game_type', table_name='matches')
