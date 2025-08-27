"""Add project members and task comments models

Revision ID: 002
Revises: 001
Create Date: 2024-08-27 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    # Create project_members table
    op.create_table('project_members',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(50), nullable=False, default='member'),
        sa.Column('joined_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id', 'user_id', name='unique_project_member')
    )
    op.create_index('idx_project_member_project', 'project_members', ['project_id'], unique=False)
    op.create_index('idx_project_member_user', 'project_members', ['user_id'], unique=False)

    # Create task_comments table
    op.create_table('task_comments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=False),
        sa.Column('author_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('is_edited', sa.Boolean(), nullable=False, default=False),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_comment_author', 'task_comments', ['author_id'], unique=False)
    op.create_index('idx_comment_created', 'task_comments', ['created_at'], unique=False)
    op.create_index('idx_comment_task', 'task_comments', ['task_id'], unique=False)


def downgrade():
    # Drop indexes
    op.drop_index('idx_comment_task', table_name='task_comments')
    op.drop_index('idx_comment_created', table_name='task_comments')
    op.drop_index('idx_comment_author', table_name='task_comments')
    op.drop_index('idx_project_member_user', table_name='project_members')
    op.drop_index('idx_project_member_project', table_name='project_members')
    
    # Drop tables
    op.drop_table('task_comments')
    op.drop_table('project_members')