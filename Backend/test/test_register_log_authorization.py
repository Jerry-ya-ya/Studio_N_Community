from pathlib import Path
from uuid import uuid4

from flask_jwt_extended import create_access_token

from models import User, db
from routes.admin import logs as log_routes


def test_register_logs_are_only_available_to_superadmins(app, client, monkeypatch):
    unique_id = uuid4().hex

    with app.app_context():
        admin = User(
            username=f'register-log-admin-{unique_id}',
            password='hashed-password',
            email=f'admin-{unique_id}@example.com',
            role='admin',
        )
        superadmin = User(
            username=f'register-log-superadmin-{unique_id}',
            password='hashed-password',
            email=f'superadmin-{unique_id}@example.com',
            role='superadmin',
        )
        db.session.add_all([admin, superadmin])
        db.session.commit()
        admin_id = admin.id
        superadmin_id = superadmin.id
        admin_token = create_access_token(identity=str(admin_id))
        superadmin_token = create_access_token(identity=str(superadmin_id))

    monkeypatch.setattr(
        log_routes,
        'read_backend_log',
        lambda filename, limit: (Path('/logs') / filename, []),
    )

    admin_headers = {'Authorization': f'Bearer {admin_token}'}
    superadmin_headers = {'Authorization': f'Bearer {superadmin_token}'}

    forbidden_response = client.get(
        '/api/superadmin/logs/register',
        headers=admin_headers,
    )
    assert forbidden_response.status_code == 403

    removed_admin_response = client.get(
        '/api/admin/logs/register',
        headers=admin_headers,
    )
    assert removed_admin_response.status_code == 404

    allowed_response = client.get(
        '/api/superadmin/logs/register',
        headers=superadmin_headers,
    )
    assert allowed_response.status_code == 200
    assert allowed_response.get_json()['type'] == 'register'

    with app.app_context():
        db.session.delete(db.session.get(User, admin_id))
        db.session.delete(db.session.get(User, superadmin_id))
        db.session.commit()
