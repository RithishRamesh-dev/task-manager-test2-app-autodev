import os
from flask import request, jsonify, send_file, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename

from app import db
from app.api import api
from app.models.attachment import Attachment
from app.models.task import Task
from app.utils.decorators import handle_api_errors, require_active_user, paginate_query
from app.utils.validators import validate_file_size, validate_mime_type
from app.utils.helpers import (
    create_api_response, generate_unique_filename, 
    allowed_file, get_file_size_formatted
)


@api.route('/tasks/<int:task_id>/attachments', methods=['POST'])
@jwt_required()
@require_active_user
@handle_api_errors
def upload_attachment(task_id):
    """Upload file attachment to a task"""
    current_user_id = get_jwt_identity()
    
    # Check if task exists and user can edit it
    task = Task.query.get(task_id)
    if not task:
        return create_api_response(False, 'Task not found', None, 404)
    
    if not task.can_user_edit(current_user_id):
        return create_api_response(False, 'Permission denied', None, 403)
    
    # Check if file is in request
    if 'file' not in request.files:
        return create_api_response(False, 'No file provided', None, 400)
    
    file = request.files['file']
    
    # Check if file is selected
    if file.filename == '':
        return create_api_response(False, 'No file selected', None, 400)
    
    # Validate file
    if not allowed_file(file.filename):
        return create_api_response(
            False, 
            'File type not allowed. Allowed types: txt, pdf, png, jpg, jpeg, gif, doc, docx, xls, xlsx',
            None, 
            400
        )
    
    # Check file size
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)  # Reset file pointer
    
    size_validation = validate_file_size(file_size)
    if not size_validation['valid']:
        return create_api_response(False, size_validation['message'], None, 400)
    
    # Get MIME type
    mime_type = file.content_type or 'application/octet-stream'
    
    # Validate MIME type
    mime_validation = validate_mime_type(mime_type)
    if not mime_validation['valid']:
        return create_api_response(False, mime_validation['message'], None, 400)
    
    try:
        # Generate unique filename
        original_filename = secure_filename(file.filename)
        unique_filename = generate_unique_filename(original_filename)
        
        # Create upload directory if it doesn't exist
        upload_dir = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        task_dir = os.path.join(upload_dir, 'tasks', str(task_id))
        os.makedirs(task_dir, exist_ok=True)
        
        # Save file
        file_path = os.path.join(task_dir, unique_filename)
        file.save(file_path)
        
        # Create attachment record
        attachment = Attachment(
            filename=unique_filename,
            original_filename=original_filename,
            file_path=file_path,
            file_size=file_size,
            mime_type=mime_type,
            task_id=task_id,
            uploaded_by=current_user_id
        )
        
        db.session.add(attachment)
        db.session.commit()
        
        return create_api_response(
            True,
            'File uploaded successfully',
            {'attachment': attachment.to_dict()},
            201
        )
        
    except Exception as e:
        db.session.rollback()
        # Try to remove file if it was created
        try:
            if 'file_path' in locals() and os.path.exists(file_path):
                os.remove(file_path)
        except:
            pass
        
        current_app.logger.error(f'File upload error: {str(e)}')
        return create_api_response(False, 'Failed to upload file', None, 500)


@api.route('/tasks/<int:task_id>/attachments', methods=['GET'])
@jwt_required()
@require_active_user
@paginate_query
@handle_api_errors
def get_task_attachments(task_id, page=1, per_page=20):
    """Get attachments for a task"""
    current_user_id = get_jwt_identity()
    
    # Check if task exists and user can view it
    task = Task.query.get(task_id)
    if not task:
        return create_api_response(False, 'Task not found', None, 404)
    
    if not task.can_user_view(current_user_id):
        return create_api_response(False, 'Access denied', None, 403)
    
    # Get attachments
    query = Attachment.query.filter_by(task_id=task_id).order_by(
        Attachment.created_at.desc()
    )
    
    attachments = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    return create_api_response(
        True,
        'Task attachments retrieved successfully',
        {
            'task_id': task_id,
            'attachments': [attachment.to_dict() for attachment in attachments.items],
            'pagination': {
                'page': attachments.page,
                'per_page': attachments.per_page,
                'total': attachments.total,
                'pages': attachments.pages,
                'has_next': attachments.has_next,
                'has_prev': attachments.has_prev
            }
        }
    )


@api.route('/attachments/<int:attachment_id>', methods=['GET'])
@jwt_required()
@require_active_user
@handle_api_errors
def get_attachment(attachment_id):
    """Get attachment details"""
    current_user_id = get_jwt_identity()
    
    attachment = Attachment.query.get(attachment_id)
    if not attachment:
        return create_api_response(False, 'Attachment not found', None, 404)
    
    if not attachment.can_user_access(current_user_id):
        return create_api_response(False, 'Access denied', None, 403)
    
    return create_api_response(
        True,
        'Attachment retrieved successfully',
        {'attachment': attachment.to_dict()}
    )


@api.route('/attachments/<int:attachment_id>/download', methods=['GET'])
@jwt_required()
@require_active_user
@handle_api_errors
def download_attachment(attachment_id):
    """Download attachment file"""
    current_user_id = get_jwt_identity()
    
    attachment = Attachment.query.get(attachment_id)
    if not attachment:
        return create_api_response(False, 'Attachment not found', None, 404)
    
    if not attachment.can_user_access(current_user_id):
        return create_api_response(False, 'Access denied', None, 403)
    
    # Check if file exists
    if not os.path.exists(attachment.file_path):
        return create_api_response(False, 'File not found on server', None, 404)
    
    try:
        return send_file(
            attachment.file_path,
            as_attachment=True,
            download_name=attachment.original_filename,
            mimetype=attachment.mime_type
        )
    except Exception as e:
        current_app.logger.error(f'File download error: {str(e)}')
        return create_api_response(False, 'Failed to download file', None, 500)


@api.route('/attachments/<int:attachment_id>', methods=['DELETE'])
@jwt_required()
@require_active_user
@handle_api_errors
def delete_attachment(attachment_id):
    """Delete attachment"""
    current_user_id = get_jwt_identity()
    
    attachment = Attachment.query.get(attachment_id)
    if not attachment:
        return create_api_response(False, 'Attachment not found', None, 404)
    
    if not attachment.can_user_delete(current_user_id):
        return create_api_response(False, 'Permission denied', None, 403)
    
    file_path = attachment.file_path
    
    try:
        # Delete from database first
        db.session.delete(attachment)
        db.session.commit()
        
        # Try to delete file
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            current_app.logger.warning(f'Could not delete file {file_path}: {str(e)}')
        
        return create_api_response(True, 'Attachment deleted successfully')
        
    except Exception as e:
        db.session.rollback()
        return create_api_response(False, 'Failed to delete attachment', None, 500)


@api.route('/attachments/my', methods=['GET'])
@jwt_required()
@require_active_user
@paginate_query
@handle_api_errors
def get_my_attachments(page=1, per_page=20):
    """Get attachments uploaded by current user"""
    current_user_id = get_jwt_identity()
    
    query = Attachment.query.filter_by(
        uploaded_by=current_user_id
    ).order_by(Attachment.created_at.desc())
    
    # Filter by file type if provided
    file_type = request.args.get('file_type')
    if file_type:
        if file_type == 'image':
            query = query.filter(Attachment.mime_type.startswith('image/'))
        elif file_type == 'document':
            doc_types = [
                'application/pdf', 'application/msword',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'application/vnd.ms-excel',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'text/plain', 'text/csv'
            ]
            query = query.filter(Attachment.mime_type.in_(doc_types))
    
    attachments = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    return create_api_response(
        True,
        'My attachments retrieved successfully',
        {
            'attachments': [attachment.to_dict() for attachment in attachments.items],
            'pagination': {
                'page': attachments.page,
                'per_page': attachments.per_page,
                'total': attachments.total,
                'pages': attachments.pages,
                'has_next': attachments.has_next,
                'has_prev': attachments.has_prev
            }
        }
    )