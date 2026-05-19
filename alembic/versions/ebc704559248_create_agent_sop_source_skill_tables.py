"""create agent sop_source skill tables

Revision ID: ebc704559248
Revises: 6536806ba68e
Create Date: 2026-05-19 10:25:08.929376

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'ebc704559248'
down_revision: Union[str, Sequence[str], None] = '6536806ba68e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create agent table without the current_skill_id FK (skill doesn't exist yet).
    op.create_table('agent',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('factory_id', sa.Uuid(), nullable=False),
    sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('purpose', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('current_skill_id', sa.Uuid(), nullable=True),
    sa.Column('runtime_status', sa.Enum('PENDING', 'DEPLOYING', 'RUNNING', 'STOPPED', 'ERROR', name='runtimestatus'), nullable=False),
    sa.Column('deployed_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['factory_id'], ['factory.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_factory_id'), 'agent', ['factory_id'], unique=False)
    # Create skill table (depends on agent).
    op.create_table('skill',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('agent_id', sa.Uuid(), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('status', sa.Enum('DRAFT', 'ACTIVE', 'ARCHIVED', name='skillstatus'), nullable=False),
    sa.Column('prompt', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('tool_specs', sa.JSON(), nullable=True),
    sa.Column('golden_test_cases', sa.JSON(), nullable=True),
    sa.Column('sop_source_set_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('generated_by_run_id', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.ForeignKeyConstraint(['agent_id'], ['agent.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_skill_agent_id'), 'skill', ['agent_id'], unique=False)
    # Now that skill exists, add the FK from agent.current_skill_id -> skill.id.
    op.create_foreign_key('fk_agent_current_skill_id', 'agent', 'skill', ['current_skill_id'], ['id'])
    # Create sop_source table.
    op.create_table('sop_source',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('factory_id', sa.Uuid(), nullable=False),
    sa.Column('type', sa.Enum('PDF', 'TRANSCRIPT', 'TABLE', 'QC_SPEC', 'CASE_LIBRARY', name='sopsourcetype'), nullable=False),
    sa.Column('storage_ref', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('metadata', sa.JSON(), nullable=True),
    sa.Column('ingested_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['factory_id'], ['factory.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sop_source_factory_id'), 'sop_source', ['factory_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_sop_source_factory_id'), table_name='sop_source')
    op.drop_table('sop_source')
    # Drop the deferred FK before dropping agent.
    op.drop_constraint('fk_agent_current_skill_id', 'agent', type_='foreignkey')
    op.drop_index(op.f('ix_skill_agent_id'), table_name='skill')
    op.drop_table('skill')
    op.drop_index(op.f('ix_agent_factory_id'), table_name='agent')
    op.drop_table('agent')
    op.execute("DROP TYPE IF EXISTS runtimestatus")
    op.execute("DROP TYPE IF EXISTS sopsourcetype")
    op.execute("DROP TYPE IF EXISTS skillstatus")
