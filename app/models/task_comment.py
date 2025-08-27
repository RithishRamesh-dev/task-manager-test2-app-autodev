from datetime import datetime
from app import db


class TaskComment(db.Model):
    """Comments on tasks"""
    __tablename__ = 'task_comments'

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False, index=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_edited = db.Column(db.Boolean, default=False, nullable=False)

    __table_args__ = (
        db.Index('idx_comment_task', 'task_id'),
        db.Index('idx_comment_author', 'author_id'),
        db.Index('idx_comment_created', 'created_at')
    )

    def __init__(self, content, task_id, author_id):
        self.content = content
        self.task_id = task_id
        self.author_id = author_id

    def update_content(self, new_content):
        """Update comment content"""
        if new_content != self.content:
            self.content = new_content
            self.is_edited = True
            self.updated_at = datetime.utcnow()

    def can_user_edit(self, user_id):
        """Check if user can edit this comment"""
        return user_id == self.author_id

    def can_user_delete(self, user_id):
        """Check if user can delete this comment"""
        # Comment author can delete, or task creator/assignee, or project owner
        if user_id == self.author_id:
            return True
        
        from app.models.task import Task
        task = Task.query.get(self.task_id)
        return task and task.can_user_edit(user_id)

    def to_dict(self, include_author=True):
        """Convert comment to dictionary"""
        data = {
            'id': self.id,
            'content': self.content,
            'task_id': self.task_id,
            'author_id': self.author_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'is_edited': self.is_edited
        }
        
        if include_author:
            from app.models.user import User
            author = User.query.get(self.author_id)
            if author:
                data['author'] = {
                    'id': author.id,
                    'username': author.username,
                    'full_name': author.full_name
                }
        
        return data

    def __repr__(self):
        return f'<TaskComment id={self.id} task_id={self.task_id}>'