from datetime import datetime
from app import db


class Attachment(db.Model):
    """File attachments for tasks"""
    __tablename__ = 'attachments'

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)  # Stored filename
    original_filename = db.Column(db.String(255), nullable=False)  # Original user filename
    file_path = db.Column(db.String(500), nullable=False)  # Full path to file
    file_size = db.Column(db.Integer, nullable=False)  # File size in bytes
    mime_type = db.Column(db.String(100), nullable=False)  # File MIME type
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False, index=True)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.Index('idx_attachment_task', 'task_id'),
        db.Index('idx_attachment_uploader', 'uploaded_by'),
        db.Index('idx_attachment_created', 'created_at')
    )

    def __init__(self, filename, original_filename, file_path, file_size, mime_type, task_id, uploaded_by):
        self.filename = filename
        self.original_filename = original_filename
        self.file_path = file_path
        self.file_size = file_size
        self.mime_type = mime_type
        self.task_id = task_id
        self.uploaded_by = uploaded_by

    def get_file_size_formatted(self):
        """Get human readable file size"""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    def is_image(self):
        """Check if attachment is an image"""
        image_types = ['image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/webp']
        return self.mime_type in image_types

    def is_document(self):
        """Check if attachment is a document"""
        doc_types = [
            'application/pdf', 'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'text/plain', 'text/csv'
        ]
        return self.mime_type in doc_types

    def can_user_access(self, user_id):
        """Check if user can access this attachment"""
        # Users can access attachment if they can view the task
        from app.models.task import Task
        task = Task.query.get(self.task_id)
        return task and task.can_user_view(user_id)

    def can_user_delete(self, user_id):
        """Check if user can delete this attachment"""
        # Only uploader or task creator/assignee can delete
        if user_id == self.uploaded_by:
            return True
        
        from app.models.task import Task
        task = Task.query.get(self.task_id)
        return task and task.can_user_edit(user_id)

    def to_dict(self):
        """Convert attachment object to dictionary"""
        return {
            'id': self.id,
            'filename': self.filename,
            'original_filename': self.original_filename,
            'file_size': self.file_size,
            'file_size_formatted': self.get_file_size_formatted(),
            'mime_type': self.mime_type,
            'task_id': self.task_id,
            'uploaded_by': self.uploaded_by,
            'created_at': self.created_at.isoformat(),
            'is_image': self.is_image(),
            'is_document': self.is_document()
        }

    def __repr__(self):
        return f'<Attachment {self.original_filename}>'