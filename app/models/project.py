from datetime import datetime
from app import db


class Project(db.Model):
    """Project model for organizing tasks"""
    __tablename__ = 'projects'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.Enum('active', 'inactive', 'completed', 'archived',
                              name='project_status'), default='active', nullable=False, index=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    tasks = db.relationship('Task', backref='project', lazy='dynamic', cascade='all, delete-orphan')
    members = db.relationship('ProjectMember', backref='project', lazy='dynamic', cascade='all, delete-orphan')

    __table_args__ = (
        db.Index('idx_project_owner', 'owner_id'),
        db.Index('idx_project_status', 'status'),
        db.Index('idx_project_created', 'created_at')
    )

    def __init__(self, name, description, owner_id):
        self.name = name
        self.description = description
        self.owner_id = owner_id

    def get_members(self):
        """Get all project members"""
        from app.models.user import User
        from app.models.project_member import ProjectMember
        return db.session.query(User).join(ProjectMember).filter(
            ProjectMember.project_id == self.id
        ).all()

    def get_member_count(self):
        """Get count of project members"""
        return self.members.count()

    def is_member(self, user_id):
        """Check if user is a member of this project"""
        from app.models.project_member import ProjectMember
        return ProjectMember.query.filter_by(
            project_id=self.id,
            user_id=user_id
        ).first() is not None

    def can_user_access(self, user_id):
        """Check if user can access this project"""
        return user_id == self.owner_id or self.is_member(user_id)

    def can_user_edit(self, user_id):
        """Check if user can edit this project"""
        return user_id == self.owner_id

    def get_task_count(self):
        """Get total number of tasks in project"""
        return self.tasks.count()

    def get_completed_task_count(self):
        """Get number of completed tasks"""
        return self.tasks.filter_by(status='completed').count()

    def get_completion_percentage(self):
        """Get project completion percentage"""
        total_tasks = self.get_task_count()
        if total_tasks == 0:
            return 0
        completed_tasks = self.get_completed_task_count()
        return (completed_tasks / total_tasks) * 100

    def to_dict(self, include_stats=False):
        """Convert project to dictionary"""
        data = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'status': self.status,
            'owner_id': self.owner_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
        
        if include_stats:
            data.update({
                'member_count': self.get_member_count(),
                'task_count': self.get_task_count(),
                'completed_tasks': self.get_completed_task_count(),
                'completion_percentage': self.get_completion_percentage()
            })
        
        return data

    def __repr__(self):
        return f'<Project {self.name}>'