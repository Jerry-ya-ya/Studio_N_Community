import os
import uuid

from flask import Blueprint, current_app, jsonify, request
from werkzeug.utils import secure_filename

from models import db, HomeNewsItem, User
from routes.admin.decorators import admin_required
from time_utils import to_taipei_iso

content_bp = Blueprint('content', __name__)

VALID_THEMES = {'cmen', 'eden'}
VALID_MEMBER_ROLES = {'superadmin', 'admin', 'member', 'user'}
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

DEFAULT_HOME_NEWS = {
    'cmen': [
        {
            'title': 'Prototype Lab Opens',
            'summary': 'A small corner for gameplay sketches, tiny tools, and strange experiments.',
            'tag': 'Studio',
        },
        {
            'title': 'Player Notes Wanted',
            'summary': 'Collecting first impressions before the next round of game-facing polish.',
            'tag': 'Community',
        },
        {
            'title': 'Devlog Queue',
            'summary': 'Future posts will track builds, experiments, and useful lessons from production.',
            'tag': 'Devlog',
        },
    ],
    'eden': [
        {
            'title': 'Knowledge Node Online',
            'summary': 'EDEN prepares a shared space for questions, references, and learning trails.',
            'tag': 'Network',
        },
        {
            'title': 'Learning Routes Drafted',
            'summary': 'Encode, Develop, Enlighten, and Nexus will shape the first content channels.',
            'tag': 'Roadmap',
        },
        {
            'title': 'Admin News Tools Planned',
            'summary': 'Community news cards are placeholders until editable publishing is unlocked.',
            'tag': 'System',
        },
    ],
}

DEFAULT_MEMBER_CONTENT = [
    {
        'name': 'Jerry-ya-ya',
        'role': 'member',
        'github_url': 'https://github.com/Jerry-ya-ya',
    }
    for index in range(1, 13)
]


def serialize_home_news(item):
    return {
        'id': item.id,
        'theme': item.theme,
        'title': item.title,
        'summary': item.summary,
        'tag': item.tag,
        'backgroundUrl': item.background_url,
        'sort_order': item.sort_order,
        'created_at': to_taipei_iso(item.created_at),
        'updated_at': to_taipei_iso(item.updated_at),
    }

def serialize_registered_member(user):
    role = user.role if user.role in VALID_MEMBER_ROLES else 'user'

    return {
        'id': user.id,
        'name': user.nickname or user.username,
        'username': user.username,
        'role': role,
        'githubUrl': user.github_url or '',
        'avatarUrl': user.avatar_url,
        'sort_order': user.id,
        'created_at': to_taipei_iso(user.created_at),
        'updated_at': None,
    }


def serialize_defaults():
    return {
        theme: [
            {
                **item,
                'id': None,
                'theme': theme,
                'backgroundUrl': None,
                'sort_order': index,
                'created_at': None,
                'updated_at': None,
            }
            for index, item in enumerate(items)
        ]
        for theme, items in DEFAULT_HOME_NEWS.items()
    }

def serialize_member_defaults():
    return [
        {
            'id': None,
            'name': item['name'],
            'role': item['role'],
            'githubUrl': item['github_url'],
            'sort_order': index,
            'created_at': None,
            'updated_at': None,
        }
        for index, item in enumerate(DEFAULT_MEMBER_CONTENT)
    ]


def grouped_home_news():
    items = HomeNewsItem.query.order_by(HomeNewsItem.theme.asc(), HomeNewsItem.sort_order.asc(), HomeNewsItem.id.asc()).all()
    if not items:
        return serialize_defaults()

    grouped = {'cmen': [], 'eden': []}
    for item in items:
        if item.theme in grouped:
            grouped[item.theme].append(serialize_home_news(item))

    return grouped


def list_registered_members():
    users = User.query.order_by(User.created_at.asc(), User.id.asc()).all()
    return [serialize_registered_member(user) for user in users]


def read_item_payload(data, default_theme=None, default_order=0):
    if not isinstance(data, dict):
        return None, ('news item must be an object', 400)

    theme = (data.get('theme') or default_theme or '').strip()
    title = (data.get('title') or '').strip()
    summary = (data.get('summary') or '').strip()
    tag = (data.get('tag') or '').strip()
    background_url = (data.get('backgroundUrl') or data.get('background_url') or '').strip()
    sort_order = data.get('sort_order', default_order)

    if theme not in VALID_THEMES:
        return None, ('theme must be cmen or eden', 400)
    if not title:
        return None, ('title is required', 400)
    if not summary:
        return None, ('summary is required', 400)
    if not tag:
        return None, ('tag is required', 400)

    try:
        sort_order = int(sort_order)
    except (TypeError, ValueError):
        return None, ('sort_order must be a number', 400)

    return {
        'theme': theme,
        'title': title[:120],
        'summary': summary,
        'tag': tag[:40],
        'background_url': background_url[:255] or None,
        'sort_order': sort_order,
    }, None


def is_allowed_image(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


@content_bp.route('/content/home-news', methods=['GET'])
def public_home_news():
    return jsonify(grouped_home_news())


@content_bp.route('/content/members', methods=['GET'])
def public_members():
    members = list_registered_members()
    if not members:
        return jsonify(serialize_member_defaults())

    return jsonify(members)


@content_bp.route('/admin/content/home-news', methods=['GET'])
@admin_required
def admin_home_news():
    return jsonify(grouped_home_news())


@content_bp.route('/admin/content/members', methods=['GET'])
@admin_required
def admin_members():
    return jsonify(list_registered_members())


@content_bp.route('/admin/content/members', methods=['PUT'])
@admin_required
def replace_members():
    return jsonify({
        'error': 'member content is generated from registered users and cannot be edited here'
    }), 405


@content_bp.route('/admin/content/home-news', methods=['PUT'])
@admin_required
def replace_home_news():
    data = request.get_json(silent=True) or {}
    next_items = []

    for theme in ['cmen', 'eden']:
        raw_items = data.get(theme, [])
        if not isinstance(raw_items, list):
            return jsonify({'error': f'{theme} must be a list'}), 400

        for index, raw_item in enumerate(raw_items):
            payload, error = read_item_payload(raw_item, default_theme=theme, default_order=index)
            if error:
                message, status = error
                return jsonify({'error': message}), status
            next_items.append(HomeNewsItem(**payload))

    HomeNewsItem.query.delete()
    db.session.add_all(next_items)
    db.session.commit()

    return jsonify(grouped_home_news())


@content_bp.route('/admin/content/home-news/items', methods=['POST'])
@admin_required
def create_home_news_item():
    data = request.get_json(silent=True) or {}
    payload, error = read_item_payload(data)
    if error:
        message, status = error
        return jsonify({'error': message}), status

    item = HomeNewsItem(**payload)
    db.session.add(item)
    db.session.commit()

    return jsonify(serialize_home_news(item)), 201


@content_bp.route('/admin/content/home-news/items/<int:item_id>', methods=['PUT'])
@admin_required
def update_home_news_item(item_id):
    item = HomeNewsItem.query.get_or_404(item_id)
    data = request.get_json(silent=True) or {}
    payload, error = read_item_payload(data, default_theme=item.theme, default_order=item.sort_order)
    if error:
        message, status = error
        return jsonify({'error': message}), status

    for key, value in payload.items():
        setattr(item, key, value)
    db.session.commit()

    return jsonify(serialize_home_news(item))


@content_bp.route('/admin/content/home-news/items/<int:item_id>/background', methods=['POST'])
@admin_required
def upload_home_news_background(item_id):
    item = HomeNewsItem.query.get_or_404(item_id)
    uploaded_file = request.files.get('file') or request.files.get('image') or request.files.get('background')

    if not uploaded_file:
        return jsonify({'error': 'No file part'}), 400
    if uploaded_file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if not is_allowed_image(uploaded_file.filename):
        return jsonify({'error': 'Invalid file type'}), 400

    upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'home-news')
    os.makedirs(upload_folder, exist_ok=True)

    original_name = secure_filename(uploaded_file.filename)
    extension = original_name.rsplit('.', 1)[1].lower()
    filename = f'{item.id}_{uuid.uuid4().hex}.{extension}'
    filepath = os.path.join(upload_folder, filename)
    uploaded_file.save(filepath)

    item.background_url = f'/static/uploads/home-news/{filename}'
    db.session.commit()

    return jsonify(serialize_home_news(item))


@content_bp.route('/admin/content/home-news/items/<int:item_id>', methods=['DELETE'])
@admin_required
def delete_home_news_item(item_id):
    item = HomeNewsItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()

    return jsonify({'message': 'home news item deleted', 'id': item_id})
