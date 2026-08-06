from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from models import db, ProjectRecruitment, Todo
from routes.auth.utils import get_current_user_from_token
from time_utils import to_taipei_text

todo_bp = Blueprint('todo', __name__)

# Todos API


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
        'assignee_name': todo.user.nickname or todo.user.username if todo.user else None,
        'claimed_by_name': todo.claimed_by.nickname or todo.claimed_by.username if todo.claimed_by else None,
        'created_at': to_taipei_text(todo.created_at),
    }


def get_project_assignee_ids(project, data):
    assign_to_team = bool(data.get('assign_to_team'))
    assignee_user_id = data.get('assignee_user_id')

    if assign_to_team:
        member_ids = [member.user_id for member in project.members]
        return sorted({project.creator_id, *member_ids})

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
        db.session.add_all(new_todos)
        db.session.commit()

        return jsonify([serialize_todo(todo) for todo in new_todos]), 201

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
        query = query.filter_by(user_id=user.id)

    if project_id:
        query = query.filter_by(project_id=project_id)

    todos = query.order_by(Todo.created_at.desc(), Todo.id.desc()).all()

    return jsonify([serialize_todo(t) for t in todos])

# U 更新待辦事項
@todo_bp.route('/todos/<int:todo_id>', methods=['PUT'])
@jwt_required()# 登入保護
def update_todo(todo_id):
    user = get_current_user_from_token()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    todo = Todo.query.filter(
        Todo.id == todo_id,
        (Todo.user_id == user.id) | (Todo.created_by_id == user.id)
    ).first()

    if not todo:
        return jsonify({'error': 'Not found'}), 404
    
    data = request.get_json(silent=True) or {}
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
        todo.duration = duration

    if 'claimed' in data:
        claimed = bool(data.get('claimed'))
        if claimed:
            if todo.claimed_by_id and todo.claimed_by_id != user.id:
                return jsonify({'error': '此任務已被其他成員佔領'}), 409
            todo.claimed_by_id = user.id
        elif todo.claimed_by_id in [None, user.id] or todo.created_by_id == user.id:
            todo.claimed_by_id = None
        else:
            return jsonify({'error': '只能取消自己佔領的任務'}), 403

    if 'done' in data:
        if data.get('done') and todo.claimed_by_id != user.id:
            return jsonify({'error': '只能完成自己佔領的任務'}), 403
        todo.done = bool(data.get('done'))

    db.session.commit()

    return jsonify(serialize_todo(todo))

# D 刪除待辦事項
@todo_bp.route('/todos/<int:todo_id>', methods=['DELETE'])
@jwt_required()# 登入保護
def delete_todo(todo_id):
    user = get_current_user_from_token()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    todo = Todo.query.filter(
        Todo.id == todo_id,
        (Todo.user_id == user.id) | (Todo.created_by_id == user.id)
    ).first()
    
    if not todo:
            return jsonify({'error': 'Not found'}), 404

    db.session.delete(todo)
    db.session.commit()
    return jsonify({'message': 'Deleted'})
