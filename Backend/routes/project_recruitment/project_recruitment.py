import json
from datetime import date

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy.exc import IntegrityError

from models import DailyCheckIn, db, ProjectRecruitment, ProjectRecruitmentMember, Todo
from log_writer import get_backend_logger
from routes.admin.decorators import admin_required
from routes.auth.utils import get_current_user_from_token
from time_utils import taipei_now, to_taipei_iso, to_taipei_text

project_recruitment_bp = Blueprint('project_recruitment', __name__)
project_logger = get_backend_logger('project_recruitment', 'project.log', message_only=True)
todo_settlement_logger = get_backend_logger('todo_settlement', 'todo_settlement.log', message_only=True)

PRIORITY_REWARD_MULTIPLIERS = [1.5, 1.3, 1.2, 1.1, 1.0]
PRIORITY_REWARD_BONUSES = [1, 2, 3, 4, 5]
DIFFICULTY_REWARD_POINTS = [2, 4, 6, 9, 13]
TODO_REWARD_COIN_DATE = date(1970, 1, 1)


def write_project_log(level, **payload):
    payload.setdefault('event', 'project_recruitment')
    payload.setdefault('logged_at', to_taipei_iso(taipei_now()))
    log_method = getattr(project_logger, level, project_logger.info)
    log_method(json.dumps(payload, ensure_ascii=False))



def write_todo_settlement_log(level, **payload):
    payload.setdefault('event', 'todo_settlement')
    payload.setdefault('logged_at', to_taipei_iso(taipei_now()))
    log_method = getattr(todo_settlement_logger, level, todo_settlement_logger.info)
    log_method(json.dumps(payload, ensure_ascii=False))
def serialize_user(user):
    return {
        'id': user.id,
        'username': user.display_username,
        'nickname': user.display_nickname,
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
        'assignee_name': todo.user.display_nickname or todo.user.display_username if todo.user else None,
        'claimed_by_name': todo.claimed_by.display_nickname or todo.claimed_by.display_username if todo.claimed_by else None,
        'reward_coins': calculate_todo_reward(todo),
        'rewardCoins': calculate_todo_reward(todo),
        'created_at': to_taipei_text(todo.created_at),
    }


def get_priority_reward_index(priority):
    try:
        value = int(priority)
    except (TypeError, ValueError):
        value = 4
    return min(len(PRIORITY_REWARD_MULTIPLIERS) - 1, max(0, value))


def get_todo_reward_breakdown(todo):
    priority_index = get_priority_reward_index(todo.priority)
    multiplier = PRIORITY_REWARD_MULTIPLIERS[priority_index]
    priority_bonus = PRIORITY_REWARD_BONUSES[priority_index]

    try:
        difficulty_value = int(todo.difficulty)
    except (TypeError, ValueError):
        difficulty_value = 6
    difficulty = difficulty_value if difficulty_value in DIFFICULTY_REWARD_POINTS else 6

    try:
        duration_value = int(todo.duration)
    except (TypeError, ValueError):
        duration_value = 0
    duration = min(5, max(0, duration_value))

    subtotal = difficulty + duration + priority_bonus
    raw_reward = subtotal * multiplier
    reward = int(raw_reward + 0.5)

    return {
        'priority': todo.priority,
        'priority_level': priority_index + 1,
        'priority_multiplier': multiplier,
        'priority_bonus': priority_bonus,
        'duration': duration,
        'difficulty': difficulty,
        'subtotal': subtotal,
        'raw_reward': round(raw_reward, 2),
        'reward_coins': reward,
        'reward_formula': f'round(({difficulty} + {duration} + {priority_bonus}) * {multiplier:.2f}) = {reward}',
    }


def calculate_todo_reward(todo):
    return get_todo_reward_breakdown(todo)['reward_coins']


def award_todo_reward(todo):
    breakdown = get_todo_reward_breakdown(todo)
    if not todo.claimed_by_id:
        return breakdown

    reward = breakdown['reward_coins']
    coin_record = DailyCheckIn.query.filter_by(
        user_id=todo.claimed_by_id,
        checkin_date=TODO_REWARD_COIN_DATE
    ).first()

    if coin_record:
        coin_record.points += reward
    else:
        db.session.add(DailyCheckIn(
            user_id=todo.claimed_by_id,
            checkin_date=TODO_REWARD_COIN_DATE,
            points=reward
        ))

    return breakdown


def serialize_todo_settlement_log_payload(project, todo, settled_by, breakdown):
    completed_by = todo.claimed_by
    return {
        'status': 'success' if todo.claimed_by_id else 'skipped',
        'reason': 'settled' if todo.claimed_by_id else 'missing_claimed_by',
        'project_id': project.id,
        'project_title': project.title,
        'todo_id': todo.id,
        'todo_text': todo.text,
        'priority': breakdown['priority'],
        'priority_level': breakdown['priority_level'],
        'priority_multiplier': breakdown['priority_multiplier'],
        'priority_bonus': breakdown['priority_bonus'],
        'duration': breakdown['duration'],
        'difficulty': breakdown['difficulty'],
        'subtotal': breakdown['subtotal'],
        'raw_reward': breakdown['raw_reward'],
        'reward_coins': breakdown['reward_coins'] if todo.claimed_by_id else 0,
        'reward_formula': breakdown['reward_formula'] if todo.claimed_by_id else '0 coins: task has no claimant',
        'completed_by_id': todo.claimed_by_id,
        'completed_by_username': completed_by.display_username if completed_by else '-',
        'completed_by_nickname': completed_by.display_nickname if completed_by else '-',
        'settled_by_id': settled_by.id,
        'settled_by_username': settled_by.display_username,
        'settled_by_nickname': settled_by.display_nickname or '-',
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
        'token_budget': project.token_budget,
        'tokenBudget': project.token_budget,
        'token_used': project.token_used,
        'tokenUsed': project.token_used,
        'token_remaining': max((project.token_budget or 0) - (project.token_used or 0), 0),
        'tokenRemaining': max((project.token_budget or 0) - (project.token_used or 0), 0),
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
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr or '').split(',')[0].strip()

    if not title:
        write_project_log(
            'warning',
            status='failed',
            reason='missing_title',
            creator_id=current_user.id,
            username=current_user.display_username,
            nickname=current_user.display_nickname or '-',
            title='-',
            summary=summary or '-',
            role_needed=role_needed or '-',
            contact=contact or '-',
            max_members=max_members or '-',
            ip=client_ip
        )
        return jsonify({'error': '請填寫專案名稱'}), 400
    if not summary:
        write_project_log(
            'warning',
            status='failed',
            reason='missing_summary',
            creator_id=current_user.id,
            username=current_user.display_username,
            nickname=current_user.display_nickname or '-',
            title=title,
            summary='-',
            role_needed=role_needed or '-',
            contact=contact or '-',
            max_members=max_members or '-',
            ip=client_ip
        )
        return jsonify({'error': '請填寫招募內容'}), 400

    if max_members in ['', None]:
        max_members = None
    else:
        try:
            max_members = int(max_members)
        except (TypeError, ValueError):
            write_project_log(
                'warning',
                status='failed',
                reason='invalid_max_members',
                creator_id=current_user.id,
                username=current_user.display_username,
                nickname=current_user.display_nickname or '-',
                title=title,
                summary=summary,
                role_needed=role_needed or '-',
                contact=contact or '-',
                max_members=data.get('max_members') or '-',
                ip=client_ip
            )
            return jsonify({'error': '人數上限必須是數字'}), 400
        if max_members < 1:
            write_project_log(
                'warning',
                status='failed',
                reason='max_members_too_low',
                creator_id=current_user.id,
                username=current_user.display_username,
                nickname=current_user.display_nickname or '-',
                title=title,
                summary=summary,
                role_needed=role_needed or '-',
                contact=contact or '-',
                max_members=max_members,
                ip=client_ip
            )
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
    write_project_log(
        'info',
        status='success',
        reason='created',
        project_id=project.id,
        creator_id=current_user.id,
        username=current_user.display_username,
        nickname=current_user.display_nickname or '-',
        title=project.title,
        summary=project.summary,
        role_needed=project.role_needed or '-',
        contact=project.contact or '-',
        max_members=project.max_members or '-',
        review_status=project.review_status,
        ip=client_ip,
        created_at=to_taipei_iso(project.created_at)
    )

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

    settlement_log_payloads = []
    if action == 'approve':
        pending_todos = [todo for todo in project.todos if todo.done and not todo.settled]
        if not pending_todos:
            return jsonify({'error': '目前沒有已完成且待結算的 Todo'}), 409

        project.review_status = 'approved'
        for todo in pending_todos:
            breakdown = award_todo_reward(todo)
            settlement_log_payloads.append(
                serialize_todo_settlement_log_payload(project, todo, current_user, breakdown)
            )
            todo.settled = True
    elif action == 'reject':
        project.review_status = 'rejected'
    else:
        return jsonify({'error': '審理動作不正確'}), 400

    db.session.commit()

    for payload in settlement_log_payloads:
        write_todo_settlement_log('info', **payload)

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
