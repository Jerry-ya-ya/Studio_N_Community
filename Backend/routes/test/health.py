from flask import Blueprint, jsonify, request

health_bp = Blueprint('health', __name__)

@health_bp.route("/healthz", methods=["GET"])
def healthz():
    # `scheme` is intentionally returned so deployment smoke tests can prove
    # that the original HTTPS scheme survived both Azure ingress hops and
    # Nginx. It contains no request or infrastructure secrets.
    return jsonify(status="ok", scheme=request.scheme), 200
