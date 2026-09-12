import json

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from log_writer import get_backend_logger
from models import db, ProjectRecruitment, ProjectRecruitmentMember, Todo
from routes.auth.utils import get_current_user_from_token
from time_utils import taipei_now, to_taipei_iso, to_taipei_text
from rate_limit import member_write_rate_limited

todo_bp = Blueprint('todo', __name__)
todo_action_logger = get_backend_logger('todo_action', 'todo_action.log', message_only=True)

PROJECT_LEVEL_TOKEN_STEP = 100

# Todos API


def display_user_name(user):
    if not user:
        return None
    return user.display_nickname or user.display_username


def write_todo_action_log(action, user, todo, **details):
    """Write one structured audit record after a successful Todo transaction."""
    if isinstance(todo, dict):
        todo_data = todo
        project_title = todo_data.get('project_title')
    else:
        todo_data = {
            'id': todo.id,
            'text': todo.text,
            'project_id': todo.project_id,
            'created_by_id': todo.created_by_id,
            'user_id': todo.user_id,
            'claimed_by_id': todo.claimed_by_id,
            'priority': todo.priority,
            'difficulty': todo.difficulty,
            'duration': todo.duration,
            'done': todo.done,
        }
        project_title = todo.project.title if todo.project else None

    payload = {
        'event': 'todo_action',
        'action': action,
        'status': 'success',
        'logged_at': to_taipei_iso(taipei_now()),
        'actor_id': user.id,
        'actor_username': user.display_username,
        'actor_nickname': user.display_nickname,
        'actor_role': user.role,
        'ip': request.headers.get('X-Forwarded-For', request.remote_addr),
        'todo_id': todo_data['id'],
        'todo_text': todo_data['text'],
        'project_id': todo_data.get('project_id'),
        'project_title': project_title,
        'created_by_id': todo_data.get('created_by_id'),
        'assignee_id': todo_data.get('user_id'),
        'claimed_by_id': todo_data.get('claimed_by_id'),
        'priority': todo_data.get('priority'),
        'difficulty': todo_data.get('difficulty'),
        'duration': todo_data.get('duration'),
        'done': todo_data.get('done'),
    }
    payload.update(details)
    todo_action_logger.info(json.dumps(payload, ensure_ascii=False))


def serialize_todo(todo):
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
        'project_id': todo.project_id,
        'project_title': todo.project.title if todo.project else None,
        'assignee_name': display_user_name(todo.user),
        'created_by_name': display_user_name(todo.creator),
        'claimed_by_name': display_user_name(todo.claimed_by),
        'created_at': to_taipei_text(todo.created_at),
    }


def serialize_project_tokens(project):
    token_budget = project.token_budget or 0
    token_used = project.token_used or 0
    token_remaining = max(token_budget - token_used, 0)

    return {
        'id': project.id,
        'token_budget': token_budget,
        'tokenBudget': token_budget,
        'token_used': token_used,
        'tokenUsed': token_used,
        'token_remaining': token_remaining,
        'tokenRemaining': token_remaining,
        'level': project.level or 1,
    }


def check_project_level_after_token_consumption(project):
    """Synchronize a project's stored level after its consumed-token total changes."""
    previous_level = max(int(project.level or 1), 1)
    calculated_level = max(int(project.token_used or 0) // PROJECT_LEVEL_TOKEN_STEP + 1, 1)
    project.level = max(previous_level, calculated_level)
    return previous_level, project.level


def user_can_access_todo(todo, user):
    if todo.user_id == user.id or todo.created_by_id == user.id:
        return True

    if todo.user_id is None and todo.project:
        member_ids = {member.user_id for member in todo.project.members}
        return user.id == todo.project.creator_id or user.id in member_ids

    return False


def get_project_assignee_ids(project, data):
    assign_to_team = bool(data.get('assign_to_team'))
    assignee_user_id = data.get('assignee_user_id')

    if assign_to_team:
        return [None]

    if not assignee_user_id:
        return [project.creator_id]

    try:
        assignee_user_id = int(assignee_user_id)
    except (TypeError, ValueError):
        return None

    allowed_ids = {project.creator_id, *(member.user_id for member in project.members)}
    if assignee_user_id not in allowed_ids:
        return None

    return [assignee_user_id]


def parse_level(value, maximum=9, default=5):
    if value in [None, '']:
        return default

    try:
        level = int(value)
    except (TypeError, ValueError):
        return None

    if level < 0 or level > maximum:
        return None

    return level

# C 新增待辦事項
@todo_bp.route('/todos', methods=['POST'])
@jwt_required()# 登入保護
@member_write_rate_limited
def add_todo():
    user = get_current_user_from_token()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json(silent=True) or {}
    text = data.get('text', '').strip()
    if not text:
        return jsonify({'error': 'Todo text is required'}), 400

    priority = parse_level(data.get('priority'), maximum=4, default=0)
    if priority is None:
        return jsonify({'error': 'Todo priority must be between 0 and 4'}), 400
    difficulty = parse_level(data.get('difficulty'))
    if difficulty is None:
        return jsonify({'error': 'Todo difficulty must be between 0 and 9'}), 400
    duration = parse_level(data.get('duration'))
    if duration is None:
        return jsonify({'error': 'Todo duration must be between 0 and 9'}), 400

    project_id = data.get('project_id')
    if project_id:
        project = ProjectRecruitment.query.get_or_404(project_id)
        if project.creator_id != user.id:
            return jsonify({'error': '只有招募隊長可以發布專案 Todo'}), 403

        assignee_ids = get_project_assignee_ids(project, data)
        if not assignee_ids:
            return jsonify({'error': '指定的成員不在這個招募團隊中'}), 400

        token_cost = priority + 1
        token_budget = project.token_budget or 0
        token_used = project.token_used or 0
        if token_used + token_cost > token_budget:
            return jsonify({'error': '專案剩餘 Token 不足，無法發布這個 Todo'}), 409

        new_todos = [
            Todo(
                text=text,
                priority=priority,
                difficulty=difficulty,
                duration=duration,
                user_id=assignee_id,
                created_by_id=user.id,
                project_id=project.id,
            )
            for assignee_id in assignee_ids
        ]
        project.token_used = token_used + token_cost
        level_before, level_after = check_project_level_after_token_consumption(project)
        db.session.add_all(new_todos)
        db.session.commit()

        for todo in new_todos:
            write_todo_action_log('create', user, todo)
        write_todo_action_log(
            'deduct_project_token',
            user,
            new_todos[0],
            token_cost=token_cost,
            token_used_before=token_used,
            token_used_after=project.token_used,
            token_budget=token_budget,
            project_level_before=level_before,
            project_level_after=level_after,
            project_level_upgraded=level_after > level_before,
        )

        return jsonify({
            'todos': [serialize_todo(todo) for todo in new_todos],
            'project': serialize_project_tokens(project),
            'token_cost': token_cost,
            'tokenCost': token_cost,
            'level_upgraded': level_after > level_before,
            'levelUpgraded': level_after > level_before,
        }), 201

    new_todo = Todo(
        text=text,
        priority=priority,
        difficulty=difficulty,
        duration=duration,
        user_id=user.id,
        created_by_id=user.id
    )

    db.session.add(new_todo)
    db.session.commit()
    write_todo_action_log('create', user, new_todo)

    return jsonify(serialize_todo(new_todo))

# R 取得所有待辦事項
@todo_bp.route('/todos', methods=['GET'])
@jwt_required()# 登入保護
def get_todos():
    user = get_current_user_from_token()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    query = Todo.query
    project_id = request.args.get('project_id')
    created_by_me = request.args.get('created_by_me') in ['1', 'true', 'True']

    if created_by_me:
        query = query.filter_by(created_by_id=user.id)
    else:
        query = query.outerjoin(
            ProjectRecruitment,
            Todo.project_id == ProjectRecruitment.id
        ).outerjoin(
            ProjectRecruitmentMember,
            (ProjectRecruitmentMember.project_id == Todo.project_id) &
            (ProjectRecruitmentMember.user_id == user.id)
        ).filter(
            (Todo.user_id == user.id) |
            (
                (Todo.user_id.is_(None)) &
                (Todo.project_id.isnot(None)) &
                (
                    (ProjectRecruitment.creator_id == user.id) |
                    (ProjectRecruitmentMember.user_id == user.id)
                )
            )
        )

    if project_id:
        query = query.filter(Todo.project_id == project_id)

    todos = query.distinct().order_by(Todo.created_at.desc(), Todo.id.desc()).all()

    return jsonify([serialize_todo(t) for t in todos])

# U 更新待辦事項
@todo_bp.route('/todos/<int:todo_id>', methods=['PUT'])
@jwt_required()# 登入保護
def update_todo(todo_id):
    user = get_current_user_from_token()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    todo = Todo.query.get(todo_id)

    if not todo or not user_can_access_todo(todo, user):
        return jsonify({'error': 'Not found'}), 404
    
    data = request.get_json(silent=True) or {}
    actions = []
    text = data.get('text')
    if text is not None:
        text = text.strip()
        if not text:
            return jsonify({'error': 'Todo text cannot be empty'}), 400
        todo.text = text

    if 'priority' in data:
        priority = parse_level(data.get('priority'), maximum=4, default=0)
        if priority is None:
            return jsonify({'error': 'Todo priority must be between 0 and 4'}), 400
        todo.priority = priority
    if 'difficulty' in data:
        difficulty = parse_level(data.get('difficulty'))
        if difficulty is None:
            return jsonify({'error': 'Todo difficulty must be between 0 and 9'}), 400
        todo.difficulty = difficulty
    if 'duration' in data:
        duration = parse_level(data.get('duration'))
        if duration is None:
            return jsonify({'error': 'Todo duration must be between 0 and 9'}), 400
        if todo.duration != duration:
            actions.append(('fill_time', {
                'duration_before': todo.duration,
                'duration_after': duration,
            }))
        todo.duration = duration

    if 'claimed' in data:
        claimed = bool(data.get('claimed'))
        if claimed:
            if todo.claimed_by_id and todo.claimed_by_id != user.id:
                return jsonify({'error': '此任務已被其他成員佔領'}), 409
            if todo.claimed_by_id != user.id:
                actions.append(('claim', {}))
            todo.claimed_by_id = user.id
        elif todo.claimed_by_id in [None, user.id] or todo.created_by_id == user.id:
            if todo.claimed_by_id is not None:
                actions.append(('unclaim', {'previous_claimed_by_id': todo.claimed_by_id}))
            todo.claimed_by_id = None
        else:
            return jsonify({'error': '只能取消自己佔領的任務'}), 403

    if 'done' in data:
        if data.get('done') and todo.claimed_by_id != user.id:
            return jsonify({'error': '只能完成自己佔領的任務'}), 403
        done = bool(data.get('done'))
        if done and not todo.done:
            actions.append(('complete', {}))
        todo.done = done

    db.session.commit()
    for action, details in actions:
        write_todo_action_log(action, user, todo, **details)

    return jsonify(serialize_todo(todo))

# D 刪除待辦事項
@todo_bp.route('/todos/<int:todo_id>', methods=['DELETE'])
@jwt_required()# 登入保護
def delete_todo(todo_id):
    user = get_current_user_from_token()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    todo = Todo.query.filter_by(id=todo_id, created_by_id=user.id).first()
    
    if not todo:
            return jsonify({'error': 'Not found'}), 404

    deleted_todo = {
        'id': todo.id,
        'text': todo.text,
        'project_id': todo.project_id,
        'project_title': todo.project.title if todo.project else None,
        'created_by_id': todo.created_by_id,
        'user_id': todo.user_id,
        'claimed_by_id': todo.claimed_by_id,
        'priority': todo.priority,
        'difficulty': todo.difficulty,
        'duration': todo.duration,
        'done': todo.done,
    }
    db.session.delete(todo)
    db.session.commit()
    write_todo_action_log('delete', user, deleted_todo)
    return jsonify({'message': 'Deleted'})
