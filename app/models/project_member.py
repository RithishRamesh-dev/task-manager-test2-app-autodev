from datetime import datetime
from app import db


class ProjectMember(db.Model):
    """Junction table for project members"""
    __tablename__ = 'project_members'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    role = db.Column(db.String(50), default='member', nullable=False)  # member, admin, etc.
    joined_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('project_id', 'user_id', name='unique_project_member'),
        db.Index('idx_project_member_project', 'project_id'),
        db.Index('idx_project_member_user', 'user_id')
    )

    def __init__(self, project_id, user_id, role='member'):
        self.project_id = project_id
        self.user_id = user_id
        self.role = role

    def to_dict(self):
        """Convert project member to dictionary"""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'user_id': self.user_id,
            'role': self.role,
            'joined_at': self.joined_at.isoformat(),
            'created_at': self.created_at.isoformat()
        }

    def __repr__(self):
        return f'<ProjectMember project_id={self.project_id} user_id={self.user_id}>'