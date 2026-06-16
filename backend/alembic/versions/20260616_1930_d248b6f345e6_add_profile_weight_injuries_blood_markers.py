"""add profile weight injuries blood markers

Revision ID: d248b6f345e6
Revises: 2c636582abfa
Create Date: 2026-06-16 19:30:00.000000

Creates:
- body_weight_log
- injury_episodes
- blood_markers
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = 'd248b6f345e6'
down_revision: Union[str, None] = '2c636582abfa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create body_weight_log
    op.create_table(
        'body_weight_log',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('weight_kg', sa.Float(), nullable=False),
        sa.Column('body_fat_pct', sa.Float(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('logged_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_body_weight_log_user_id', 'body_weight_log', ['user_id'])
    op.create_index('ix_body_weight_log_user_time', 'body_weight_log', ['user_id', 'logged_at'])

    # 2. Create injury_episodes
    op.create_table(
        'injury_episodes',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('body_part', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('severity', sa.Integer(), nullable=True),
        sa.Column('status', sa.Enum('active', 'recovering', 'resolved', name='injurystatus'), nullable=False),
        sa.Column('occurred_at', sa.Date(), nullable=False),
        sa.Column('resolved_at', sa.Date(), nullable=True),
        sa.Column('exercises_to_avoid', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_injury_episodes_user_id', 'injury_episodes', ['user_id'])
    op.create_index('ix_injury_episodes_user_status', 'injury_episodes', ['user_id', 'status'])

    # 3. Create blood_markers
    op.create_table(
        'blood_markers',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('marker', sa.String(length=80), nullable=False),
        sa.Column('display_name', sa.String(length=160), nullable=True),
        sa.Column('value_num', sa.Float(), nullable=True),
        sa.Column('value_text', sa.String(length=40), nullable=True),
        sa.Column('unit', sa.String(length=40), nullable=True),
        sa.Column('ref_text', sa.String(length=80), nullable=True),
        sa.Column('flag', sa.String(length=10), nullable=True),
        sa.Column('measured_at', sa.Date(), nullable=False),
        sa.Column('lab_name', sa.String(length=160), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_blood_markers_user_id', 'blood_markers', ['user_id'])
    op.create_index('ix_blood_markers_measured_at', 'blood_markers', ['measured_at'])
    op.create_index('ix_blood_markers_user_marker_time', 'blood_markers', ['user_id', 'marker', 'measured_at'])


def downgrade() -> None:
    # 1. Drop blood_markers
    op.drop_index('ix_blood_markers_user_marker_time', table_name='blood_markers')
    op.drop_index('ix_blood_markers_measured_at', table_name='blood_markers')
    op.drop_index('ix_blood_markers_user_id', table_name='blood_markers')
    op.drop_table('blood_markers')

    # 2. Drop injury_episodes
    op.drop_index('ix_injury_episodes_user_status', table_name='injury_episodes')
    op.drop_index('ix_injury_episodes_user_id', table_name='injury_episodes')
    op.drop_table('injury_episodes')
    
    # Drop Enum type
    sa.Enum('active', 'recovering', 'resolved', name='injurystatus').drop(op.get_bind(), checkfirst=False)

    # 3. Drop body_weight_log
    op.drop_index('ix_body_weight_log_user_time', table_name='body_weight_log')
    op.drop_index('ix_body_weight_log_user_id', table_name='body_weight_log')
    op.drop_table('body_weight_log')
