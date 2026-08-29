from flask import Blueprint, jsonify
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from models import News, ScheduleState
from time_utils import to_taipei_iso

from celery_worker.crawler.logic import fetch_and_store_news
from celery_worker.task import hello
from flask_jwt_extended import jwt_required
from routes.admin.decorators import admin_required

crawler_bp = Blueprint('crawler_bp', __name__)

@crawler_bp.route('/crawler/fetch', methods=['POST'])
@admin_required
def fetch_news_api():
    added = fetch_and_store_news()
    return jsonify({'message': f'{added} new items added.'})

@crawler_bp.route('/crawler/news', methods=['GET'])
@jwt_required()
def get_saved_news():
    news = News.query.order_by(News.created_at.desc()).limit(30).all()
    return jsonify([
        {
            'title': n.title,
            'url': n.url,
            'created_at': to_taipei_iso(n.created_at)
        }
        for n in news
    ])

@crawler_bp.route('/crawler/info', methods=['GET'])
def get_schedule_info():
    state = ScheduleState.query.filter_by(job_name="news_crawler").first()
    return jsonify({
        'last_run': to_taipei_iso(state.last_run) if state else None,
        'next_run': to_taipei_iso(state.next_run) if state else None
    })

@crawler_bp.route('/crawler/test', methods=['POST'])
@admin_required
def test_crawler():
    hello.delay()
    return jsonify({'message': 'Crawler is working!'})
