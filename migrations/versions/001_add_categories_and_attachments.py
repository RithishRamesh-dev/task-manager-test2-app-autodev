"""Add categories and attachments models

Revision ID: 001
Revises: 
Create Date: 2024-08-27 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add missing columns to users table
    op.add_column('users', sa.Column('first_name', sa.String(100), nullable=True))
    op.add_column('users', sa.Column('last_name', sa.String(100), nullable=True))
    op.add_column('users', sa.Column('is_verified', sa.Boolean(), nullable=True, default=False))
    
    # Create categories table
    op.create_table('categories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('color', sa.String(7), nullable=False, default='#007bff'),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', 'user_id', name='unique_category_per_user')
    )
    op.create_index('idx_category_user', 'categories', ['user_id'], unique=False)

    # Create task_categories junction table
    op.create_table('task_categories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('task_id', 'category_id', name='unique_task_category')
    )
    op.create_index('idx_task_category_category', 'task_categories', ['category_id'], unique=False)
    op.create_index('idx_task_category_task', 'task_categories', ['task_id'], unique=False)

    # Create attachments table
    op.create_table('attachments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('original_filename', sa.String(255), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('mime_type', sa.String(100), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=False),
        sa.Column('uploaded_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_attachment_created', 'attachments', ['created_at'], unique=False)
    op.create_index('idx_attachment_task', 'attachments', ['task_id'], unique=False)
    op.create_index('idx_attachment_uploader', 'attachments', ['uploaded_by'], unique=False)

    # Update existing users to have the new required fields
    # This is a data migration - set default values for existing users
    op.execute("UPDATE users SET first_name = 'Unknown' WHERE first_name IS NULL")
    op.execute("UPDATE users SET last_name = 'User' WHERE last_name IS NULL")
    op.execute("UPDATE users SET is_verified = false WHERE is_verified IS NULL")
    
    # Make the columns non-nullable after setting default values
    op.alter_column('users', 'first_name', nullable=False)
    op.alter_column('users', 'last_name', nullable=False)
    op.alter_column('users', 'is_verified', nullable=False)


def downgrade():
    # Drop indexes
    op.drop_index('idx_attachment_uploader', table_name='attachments')
    op.drop_index('idx_attachment_task', table_name='attachments')
    op.drop_index('idx_attachment_created', table_name='attachments')
    op.drop_index('idx_task_category_task', table_name='task_categories')
    op.drop_index('idx_task_category_category', table_name='task_categories')
    op.drop_index('idx_category_user', table_name='categories')
    
    # Drop tables
    op.drop_table('attachments')
    op.drop_table('task_categories')
    op.drop_table('categories')
    
    # Remove columns from users table
    op.drop_column('users', 'is_verified')
    op.drop_column('users', 'last_name')
    op.drop_column('users', 'first_name')