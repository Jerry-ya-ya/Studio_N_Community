from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy.exc import IntegrityError

from models import db, ProjectRecruitment, ProjectRecruitmentMember, Todo
from routes.admin.decorators import admin_required
from routes.auth.utils import get_current_user_from_token
from time_utils import to_taipei_text

project_recruitment_bp = Blueprint('project_recruitment', __name__)


def serialize_user(user):
    return {
        'id': user.id,
        'username': user.username,
        'nickname': user.nickname,
        'avatar_url': user.avatar_url,
        'role': user.role,
    }


def serialize_member(member):
    return {
        'id': member.id,
        'message': member.message,
        'created_at': to_taipei_text(member.created_at),
        'user': serialize_user(member.user),
    }


def serialize_project_todo(todo):
    return {
        'id': todo.id,
        'text': todo.text,
        'done': todo.done,
        'settled': todo.settled,
        'priority': todo.priority,
        'difficulty': todo.difficulty,
        'duration': todo.duration,
        'user_id': todo.user_id,
        'created_by_id': todo.created_by_id,
        'claimed_by_id': todo.claimed_by_id,
        'assignee_name': todo.user.nickname or todo.user.username if todo.user else None,
        'claimed_by_name': todo.claimed_by.nickname or todo.claimed_by.username if todo.claimed_by else None,
        'created_at': to_taipei_text(todo.created_at),
    }


def serialize_project(project, current_user):
    member_user_ids = {member.user_id for member in project.members}

    return {
        'id': project.id,
        'title': project.title,
        'summary': project.summary,
        'role_needed': project.role_needed,
        'contact': project.contact,
        'max_members': project.max_members,
        'review_status': project.review_status,
        'created_at': to_taipei_text(project.created_at),
        'creator': serialize_user(project.creator),
        'members': [serialize_member(member) for member in project.members],
        'todos': [
            serialize_project_todo(todo)
            for todo in sorted(project.todos, key=lambda item: (item.done, item.priority, item.id))
        ],
        'member_count': len(project.members),
        'joined_by_me': current_user.id in member_user_ids,
        'owned_by_me': project.creator_id == current_user.id,
    }


@project_recruitment_bp.route('/project-recruitments', methods=['GET'])
@jwt_required()
def list_project_recruitments():
    current_user = get_current_user_from_token()
    if not current_user:
        return jsonify({'error': 'User not found'}), 404

    projects = ProjectRecruitment.query.order_by(ProjectRecruitment.created_at.desc()).all()
    return jsonify([serialize_project(project, current_user) for project in projects])


@project_recruitment_bp.route('/admin/project-recruitments', methods=['GET'])
@admin_required
def admin_list_project_recruitments():
    current_user = get_current_user_from_token()
    if not current_user:
        return jsonify({'error': 'User not found'}), 404

    projects = ProjectRecruitment.query.order_by(ProjectRecruitment.created_at.desc()).all()
    return jsonify([serialize_project(project, current_user) for project in projects])


@project_recruitment_bp.route('/admin/project-todos/<int:todo_id>/difficulty', methods=['PUT'])
@admin_required
def admin_update_project_todo_difficulty(todo_id):
    current_user = get_current_user_from_token()
    if not current_user:
        return jsonify({'error': 'User not found'}), 404

    todo = Todo.query.filter(Todo.id == todo_id, Todo.project_id.isnot(None)).first_or_404()
    if not todo.done or todo.settled:
        return jsonify({'error': 'Only completed unsettled project todos can be scored'}), 409

    data = request.get_json(silent=True) or {}

    try:
        difficulty = int(data.get('difficulty'))
    except (TypeError, ValueError):
        return jsonify({'error': 'Todo difficulty must be one of 2, 4, 6, 9, 13'}), 400

    if difficulty not in [2, 4, 6, 9, 13]:
        return jsonify({'error': 'Todo difficulty must be one of 2, 4, 6, 9, 13'}), 400

    todo.difficulty = difficulty
    db.session.commit()

    return jsonify(serialize_project_todo(todo))


@project_recruitment_bp.route('/project-recruitments', methods=['POST'])
@jwt_required()
def create_project_recruitment():
    current_user = get_current_user_from_token()
    if not current_user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json(silent=True) or {}
    title = data.get('title', '').strip()
    summary = data.get('summary', '').strip()
    role_needed = data.get('role_needed', '').strip() or None
    contact = data.get('contact', '').strip() or None
    max_members = data.get('max_members')

    if not title:
        return jsonify({'error': '請填寫專案名稱'}), 400
    if not summary:
        return jsonify({'error': '請填寫招募內容'}), 400

    if max_members in ['', None]:
        max_members = None
    else:
        try:
            max_members = int(max_members)
        except (TypeError, ValueError):
            return jsonify({'error': '人數上限必須是數字'}), 400
        if max_members < 1:
            return jsonify({'error': '人數上限至少為 1'}), 400

    project = ProjectRecruitment(
        title=title,
        summary=summary,
        role_needed=role_needed,
        contact=contact,
        max_members=max_members,
        creator_id=current_user.id,
    )
    db.session.add(project)
    db.session.commit()

    return jsonify(serialize_project(project, current_user)), 201


@project_recruitment_bp.route('/project-recruitments/<int:project_id>/join', methods=['POST'])
@jwt_required()
def join_project_recruitment(project_id):
    current_user = get_current_user_from_token()
    if not current_user:
        return jsonify({'error': 'User not found'}), 404

    project = ProjectRecruitment.query.get_or_404(project_id)
    if project.creator_id == current_user.id:
        return jsonify({'error': '不能登記加入自己建立的招募'}), 400

    if project.max_members is not None and len(project.members) >= project.max_members:
        return jsonify({'error': '招募名額已滿'}), 400

    data = request.get_json(silent=True) or {}
    message = data.get('message', '').strip() or None
    membership = ProjectRecruitmentMember(
        project_id=project.id,
        user_id=current_user.id,
        message=message,
    )

    db.session.add(membership)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({'message': '你已經登記加入此招募'}), 200

    return jsonify(serialize_project(project, current_user))


@project_recruitment_bp.route('/project-recruitments/<int:project_id>/submit-review', methods=['POST'])
@jwt_required()
def submit_project_review(project_id):
    current_user = get_current_user_from_token()
    if not current_user:
        return jsonify({'error': 'User not found'}), 404

    project = ProjectRecruitment.query.get_or_404(project_id)
    if project.creator_id != current_user.id:
        return jsonify({'error': '只有組長可以提交專案完成審理'}), 403
    if project.review_status == 'pending':
        return jsonify({'error': '此專案已在審理中'}), 409

    pending_todos = [todo for todo in project.todos if todo.done and not todo.settled]
    if not pending_todos:
        return jsonify({'error': '目前沒有已完成且待結算的 Todo'}), 409

    project.review_status = 'pending'
    db.session.commit()

    return jsonify(serialize_project(project, current_user))


@project_recruitment_bp.route('/admin/project-recruitments/<int:project_id>/review', methods=['POST'])
@admin_required
def review_project_recruitment(project_id):
    current_user = get_current_user_from_token()
    if not current_user:
        return jsonify({'error': 'User not found'}), 404

    project = ProjectRecruitment.query.get_or_404(project_id)
    data = request.get_json(silent=True) or {}
    action = data.get('action')

    if project.review_status != 'pending':
        return jsonify({'error': '此專案目前不在待審理狀態'}), 409
    if action == 'approve':
        pending_todos = [todo for todo in project.todos if todo.done and not todo.settled]
        if not pending_todos:
            return jsonify({'error': '目前沒有已完成且待結算的 Todo'}), 409

        project.review_status = 'approved'
        for todo in pending_todos:
            todo.settled = True
    elif action == 'reject':
        project.review_status = 'rejected'
    else:
        return jsonify({'error': '審理動作不正確'}), 400

    db.session.commit()

    return jsonify(serialize_project(project, current_user))


@project_recruitment_bp.route('/project-recruitments/<int:project_id>', methods=['DELETE'])
@jwt_required()
def delete_project_recruitment(project_id):
    current_user = get_current_user_from_token()
    if not current_user:
        return jsonify({'error': 'User not found'}), 404

    project = ProjectRecruitment.query.get_or_404(project_id)
    if project.creator_id != current_user.id:
        return jsonify({'error': '只能刪除自己發布的招募'}), 403

    db.session.delete(project)
    db.session.commit()

    return jsonify({'message': '招募已刪除', 'id': project_id})


@project_recruitment_bp.route('/project-recruitments/<int:project_id>/join', methods=['DELETE'])
@jwt_required()
def leave_project_recruitment(project_id):
    current_user = get_current_user_from_token()
    if not current_user:
        return jsonify({'error': 'User not found'}), 404

    membership = ProjectRecruitmentMember.query.filter_by(
        project_id=project_id,
        user_id=current_user.id
    ).first()

    if not membership:
        return jsonify({'error': '你尚未登記加入此招募'}), 404

    project = membership.project
    db.session.delete(membership)
    db.session.commit()

    return jsonify(serialize_project(project, current_user))
