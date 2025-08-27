from datetime import datetime
from app import db


class Category(db.Model):
    """Categories for organizing tasks"""
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    color = db.Column(db.String(7), nullable=False, default='#007bff')  # Hex color code
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    task_categories = db.relationship('TaskCategory', backref='category', lazy='dynamic', cascade='all, delete-orphan')

    __table_args__ = (
        db.UniqueConstraint('name', 'user_id', name='unique_category_per_user'),
        db.Index('idx_category_user', 'user_id')
    )

    def __init__(self, name, color, user_id):
        self.name = name
        self.color = color
        self.user_id = user_id

    def get_tasks(self):
        """Get all tasks assigned to this category"""
        from app.models.task import Task
        return db.session.query(Task).join(TaskCategory).filter(
            TaskCategory.category_id == self.id
        ).all()

    def get_tasks_count(self):
        """Get count of tasks in this category"""
        return self.task_categories.count()

    def to_dict(self, include_task_count=False):
        """Convert category object to dictionary"""
        data = {
            'id': self.id,
            'name': self.name,
            'color': self.color,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
        
        if include_task_count:
            data['task_count'] = self.get_tasks_count()
        
        return data

    def __repr__(self):
        return f'<Category {self.name}>'


class TaskCategory(db.Model):
    """Junction table for many-to-many relationship between tasks and categories"""
    __tablename__ = 'task_categories'

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('task_id', 'category_id', name='unique_task_category'),
        db.Index('idx_task_category_task', 'task_id'),
        db.Index('idx_task_category_category', 'category_id')
    )

    def __init__(self, task_id, category_id):
        self.task_id = task_id
        self.category_id = category_id

    def to_dict(self):
        """Convert task-category relationship to dictionary"""
        return {
            'id': self.id,
            'task_id': self.task_id,
            'category_id': self.category_id,
            'created_at': self.created_at.isoformat()
        }

    def __repr__(self):
        return f'<TaskCategory task_id={self.task_id} category_id={self.category_id}>'