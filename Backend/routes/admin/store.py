import os
from decimal import Decimal, InvalidOperation

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import jwt_required

from image_upload import InvalidImageError, save_validated_image
from models import StoreProduct, StorePurchase, db
from routes.admin.decorators import superadmin_required
from routes.auth.utils import get_current_user_from_token
from time_utils import taipei_now, to_taipei_iso


store_bp = Blueprint('store', __name__)

DEFAULT_PRODUCT_IMAGES = {'bean', 'gift', 'ticket'}


def serialize_product(product):
    return {
        'id': product.id,
        'name': product.name,
        'description': product.description,
        'price': float(product.price),
        'stock': product.stock,
        'isLimited': product.is_limited,
        'isPublished': product.is_published,
        'imageType': product.image_type,
        'imageValue': product.image_value,
        'createdAt': to_taipei_iso(product.created_at),
        'updatedAt': to_taipei_iso(product.updated_at),
    }


def serialize_purchase(purchase):
    return {
        'id': purchase.id,
        'productId': purchase.product_id,
        'productName': purchase.product_name,
        'unitPrice': float(purchase.unit_price),
        'purchasedAt': to_taipei_iso(purchase.purchased_at),
    }


def read_product_payload(data, product=None):
    if not isinstance(data, dict):
        return None, ('商品資料格式錯誤', 400)

    values = {}
    if product is None or 'name' in data:
        name = data.get('name')
        if not isinstance(name, str) or not name.strip():
            return None, ('請輸入商品名稱', 400)
        values['name'] = name.strip()[:120]

    if product is None or 'description' in data:
        description = data.get('description', '')
        if not isinstance(description, str):
            return None, ('商品說明格式錯誤', 400)
        values['description'] = description.strip()[:2000]

    if product is None or 'price' in data:
        try:
            price = Decimal(str(data.get('price'))).quantize(Decimal('0.01'))
        except (InvalidOperation, TypeError, ValueError):
            return None, ('價格必須是有效數字', 400)
        if not price.is_finite() or price < 0 or price > Decimal('9999999999.99'):
            return None, ('價格必須介於 0 與 9,999,999,999.99', 400)
        values['price'] = price

    if product is None or 'stock' in data:
        stock = data.get('stock')
        if isinstance(stock, bool) or not isinstance(stock, int) or stock < 0:
            return None, ('庫存必須是 0 以上的整數', 400)
        values['stock'] = stock

    for json_key, model_key, default in (
        ('isLimited', 'is_limited', True),
        ('isPublished', 'is_published', False),
    ):
        if product is None or json_key in data:
            value = data.get(json_key, default)
            if not isinstance(value, bool):
                return None, (f'{json_key} 必須是布林值', 400)
            values[model_key] = value

    if product is None or 'imageType' in data or 'imageValue' in data:
        current_type = product.image_type if product else 'default'
        current_value = product.image_value if product else 'bean'
        image_type = data.get('imageType', current_type)
        image_value = data.get('imageValue', current_value)
        if image_type != 'default':
            return None, ('請透過圖片上傳功能設定自訂圖片', 400)
        if image_value not in DEFAULT_PRODUCT_IMAGES:
            return None, ('預設圖片不存在', 400)
        values['image_type'] = image_type
        values['image_value'] = image_value

    future_limited = values.get('is_limited', product.is_limited if product else True)
    future_published = values.get(
        'is_published', product.is_published if product else False
    )
    future_stock = values.get('stock', product.stock if product else 0)
    if future_limited and future_published and future_stock == 0:
        return None, ('限量商品需有庫存才能上架', 400)

    return values, None


@store_bp.route('/superadmin/store/products', methods=['GET'])
@superadmin_required
def list_products():
    products = StoreProduct.query.order_by(StoreProduct.updated_at.desc()).all()
    return jsonify([serialize_product(product) for product in products])


@store_bp.route('/superadmin/store/products', methods=['POST'])
@superadmin_required
def create_product():
    values, error = read_product_payload(request.get_json(silent=True))
    if error:
        return jsonify({'error': error[0]}), error[1]

    actor = get_current_user_from_token()
    product = StoreProduct(**values, created_by_id=actor.id if actor else None)
    db.session.add(product)
    db.session.commit()
    return jsonify(serialize_product(product)), 201


@store_bp.route('/superadmin/store/products/<int:product_id>', methods=['PUT'])
@superadmin_required
def update_product(product_id):
    product = db.session.get(StoreProduct, product_id)
    if not product:
        return jsonify({'error': '找不到商品'}), 404

    values, error = read_product_payload(request.get_json(silent=True), product)
    if error:
        return jsonify({'error': error[0]}), error[1]
    for key, value in values.items():
        setattr(product, key, value)
    db.session.commit()
    return jsonify(serialize_product(product))


@store_bp.route('/superadmin/store/products/<int:product_id>/restock', methods=['POST'])
@superadmin_required
def restock_product(product_id):
    product = db.session.get(StoreProduct, product_id)
    if not product:
        return jsonify({'error': '找不到商品'}), 404
    data = request.get_json(silent=True) or {}
    quantity = data.get('quantity')
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
        return jsonify({'error': '補貨數量必須是大於 0 的整數'}), 400
    if product.stock + quantity > 2_147_483_647:
        return jsonify({'error': '庫存數量超過上限'}), 400

    product.stock += quantity
    db.session.commit()
    return jsonify(serialize_product(product))


@store_bp.route('/superadmin/store/products/<int:product_id>/image', methods=['POST'])
@superadmin_required
def upload_product_image(product_id):
    product = db.session.get(StoreProduct, product_id)
    if not product:
        return jsonify({'error': '找不到商品'}), 404
    image = request.files.get('image')
    if not image or not image.filename:
        return jsonify({'error': '請選擇圖片'}), 400

    upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'store')
    try:
        filename = save_validated_image(image, upload_folder, f'product-{product.id}')
    except InvalidImageError as error:
        return jsonify({'error': str(error)}), 400

    product.image_type = 'upload'
    product.image_value = f'/static/uploads/store/{filename}'
    db.session.commit()
    return jsonify(serialize_product(product))


@store_bp.route('/store/products', methods=['GET'])
@jwt_required()
def list_published_products():
    if not get_current_user_from_token():
        return jsonify({'error': 'User not found'}), 404

    products = StoreProduct.query.filter_by(is_published=True).order_by(
        StoreProduct.updated_at.desc(), StoreProduct.id.desc()
    ).all()
    response = jsonify([serialize_product(product) for product in products])
    response.headers['Cache-Control'] = 'no-store'
    return response


@store_bp.route('/store/products/<int:product_id>/purchase', methods=['POST'])
@jwt_required()
def purchase_product(product_id):
    user = get_current_user_from_token()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    product = db.session.get(StoreProduct, product_id)
    if not product or not product.is_published:
        return jsonify({'error': '商品不存在或已下架'}), 404
    if product.is_limited and product.stock <= 0:
        return jsonify({'error': '商品已售完'}), 409

    conditions = [
        StoreProduct.id == product_id,
        StoreProduct.is_published.is_(True),
        StoreProduct.is_limited.is_(product.is_limited),
    ]
    values = {'updated_at': taipei_now()}
    if product.is_limited:
        conditions.append(StoreProduct.stock > 0)
        values['stock'] = StoreProduct.stock - 1

    updated = StoreProduct.query.filter(*conditions).update(
        values, synchronize_session=False
    )
    if updated != 1:
        db.session.rollback()
        return jsonify({'error': '商品狀態已變更，請重新整理後再試'}), 409

    purchase = StorePurchase(
        product_id=product.id,
        user_id=user.id,
        product_name=product.name,
        unit_price=product.price,
    )
    db.session.add(purchase)
    db.session.commit()
    db.session.refresh(product)
    return jsonify({
        'message': '購買成功',
        'purchase': serialize_purchase(purchase),
        'product': serialize_product(product),
    }), 201
