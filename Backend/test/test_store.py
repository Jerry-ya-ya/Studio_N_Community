from io import BytesIO
from pathlib import Path
from uuid import uuid4

import pytest
from flask_jwt_extended import create_access_token
from PIL import Image

from models import StoreProduct, StorePurchase, User, db


@pytest.fixture()
def store_accounts(app):
    suffix = uuid4().hex
    with app.app_context():
        superadmin = User(
            username=f'store-super-{suffix}',
            email=f'store-super-{suffix}@example.com',
            password='test-password',
            role='superadmin',
            email_verified=True,
        )
        admin = User(
            username=f'store-admin-{suffix}',
            email=f'store-admin-{suffix}@example.com',
            password='test-password',
            role='admin',
            email_verified=True,
        )
        user = User(
            username=f'store-user-{suffix}',
            email=f'store-user-{suffix}@example.com',
            password='test-password',
            role='user',
            email_verified=True,
        )
        db.session.add_all([superadmin, admin, user])
        db.session.commit()
        result = {
            'super_id': superadmin.id,
            'super_token': create_access_token(identity=str(superadmin.id)),
            'admin_id': admin.id,
            'admin_token': create_access_token(identity=str(admin.id)),
            'user_id': user.id,
            'user_token': create_access_token(identity=str(user.id)),
        }

    yield result

    with app.app_context():
        products = StoreProduct.query.filter_by(created_by_id=result['super_id']).all()
        StorePurchase.query.filter_by(user_id=result['user_id']).delete(
            synchronize_session=False
        )
        for product in products:
            if product.image_type == 'upload':
                upload = Path(app.root_path) / product.image_value.lstrip('/')
                upload.unlink(missing_ok=True)
            db.session.delete(product)
        User.query.filter(User.id.in_([
            result['super_id'], result['admin_id'], result['user_id']
        ])).delete(
            synchronize_session=False
        )
        db.session.commit()


def bearer(token):
    return {'Authorization': f'Bearer {token}'}


def product_payload(**overrides):
    payload = {
        'name': '限定魔豆',
        'description': '測試商品',
        'price': 120,
        'stock': 3,
        'isLimited': True,
        'isPublished': True,
        'imageType': 'default',
        'imageValue': 'bean',
    }
    payload.update(overrides)
    return payload


def test_store_endpoints_require_superadmin(client, store_accounts):
    endpoint = '/api/superadmin/store/products'
    assert client.get(endpoint).status_code == 401
    assert client.get(endpoint, headers=bearer(store_accounts['admin_token'])).status_code == 403


def test_superadmin_can_create_edit_publish_and_restock(client, store_accounts):
    headers = bearer(store_accounts['super_token'])
    created = client.post(
        '/api/superadmin/store/products', headers=headers, json=product_payload()
    )
    assert created.status_code == 201
    product = created.get_json()
    assert product['name'] == '限定魔豆'
    assert product['price'] == 120.0
    assert product['stock'] == 3
    assert product['isPublished'] is True

    product_id = product['id']
    updated = client.put(
        f'/api/superadmin/store/products/{product_id}',
        headers=headers,
        json={'name': '新版魔豆', 'price': 150.5, 'isPublished': False},
    )
    assert updated.status_code == 200
    assert updated.get_json()['name'] == '新版魔豆'
    assert updated.get_json()['price'] == 150.5
    assert updated.get_json()['isPublished'] is False

    restocked = client.post(
        f'/api/superadmin/store/products/{product_id}/restock',
        headers=headers,
        json={'quantity': 7},
    )
    assert restocked.status_code == 200
    assert restocked.get_json()['stock'] == 10

    listing = client.get('/api/superadmin/store/products', headers=headers)
    assert listing.status_code == 200
    assert product_id in [item['id'] for item in listing.get_json()]


@pytest.mark.parametrize(
    ('payload', 'message'),
    [
        (product_payload(name=''), '請輸入商品名稱'),
        (product_payload(price=-1), '價格必須介於'),
        (product_payload(stock=-1), '庫存必須是'),
        (product_payload(stock=0), '限量商品需有庫存'),
        (product_payload(imageValue='missing'), '預設圖片不存在'),
    ],
)
def test_product_validation(client, store_accounts, payload, message):
    response = client.post(
        '/api/superadmin/store/products',
        headers=bearer(store_accounts['super_token']),
        json=payload,
    )
    assert response.status_code == 400
    assert message in response.get_json()['error']


def test_product_image_upload(client, store_accounts):
    headers = bearer(store_accounts['super_token'])
    created = client.post(
        '/api/superadmin/store/products',
        headers=headers,
        json=product_payload(isPublished=False),
    ).get_json()
    image_bytes = BytesIO()
    Image.new('RGB', (8, 8), color=(40, 180, 90)).save(image_bytes, format='PNG')
    image_bytes.seek(0)

    response = client.post(
        f"/api/superadmin/store/products/{created['id']}/image",
        headers=headers,
        data={'image': (image_bytes, 'product.png')},
        content_type='multipart/form-data',
    )

    assert response.status_code == 200
    product = response.get_json()
    assert product['imageType'] == 'upload'
    assert product['imageValue'].startswith('/static/uploads/store/product-')


def test_user_store_only_lists_published_products(client, store_accounts):
    headers = bearer(store_accounts['super_token'])
    published = client.post(
        '/api/superadmin/store/products', headers=headers, json=product_payload()
    ).get_json()
    draft = client.post(
        '/api/superadmin/store/products',
        headers=headers,
        json=product_payload(name='草稿商品', isPublished=False),
    ).get_json()

    response = client.get(
        '/api/store/products', headers=bearer(store_accounts['user_token'])
    )

    assert response.status_code == 200
    assert response.headers['Cache-Control'] == 'no-store'
    listed_ids = [item['id'] for item in response.get_json()]
    assert published['id'] in listed_ids
    assert draft['id'] not in listed_ids


def test_user_can_purchase_product_and_limited_stock_is_decremented(
    client, app, store_accounts
):
    created = client.post(
        '/api/superadmin/store/products',
        headers=bearer(store_accounts['super_token']),
        json=product_payload(stock=1),
    ).get_json()
    endpoint = f"/api/store/products/{created['id']}/purchase"
    headers = bearer(store_accounts['user_token'])

    purchased = client.post(endpoint, headers=headers)
    sold_out = client.post(endpoint, headers=headers)

    assert purchased.status_code == 201
    assert purchased.get_json()['product']['stock'] == 0
    assert purchased.get_json()['purchase']['productName'] == '限定魔豆'
    assert sold_out.status_code == 409
    assert sold_out.get_json()['error'] == '商品已售完'
    with app.app_context():
        order = StorePurchase.query.filter_by(
            user_id=store_accounts['user_id'], product_id=created['id']
        ).one()
        assert float(order.unit_price) == 120.0


def test_user_cannot_purchase_draft_and_unlimited_stock_does_not_change(
    client, store_accounts
):
    admin_headers = bearer(store_accounts['super_token'])
    draft = client.post(
        '/api/superadmin/store/products',
        headers=admin_headers,
        json=product_payload(isPublished=False),
    ).get_json()
    unlimited = client.post(
        '/api/superadmin/store/products',
        headers=admin_headers,
        json=product_payload(name='不限量商品', stock=0, isLimited=False),
    ).get_json()
    user_headers = bearer(store_accounts['user_token'])

    assert client.post(
        f"/api/store/products/{draft['id']}/purchase", headers=user_headers
    ).status_code == 404
    purchased = client.post(
        f"/api/store/products/{unlimited['id']}/purchase", headers=user_headers
    )
    assert purchased.status_code == 201
    assert purchased.get_json()['product']['stock'] == 0


def test_user_store_requires_authentication(client):
    assert client.get('/api/store/products').status_code == 401
    assert client.post('/api/store/products/1/purchase').status_code == 401
