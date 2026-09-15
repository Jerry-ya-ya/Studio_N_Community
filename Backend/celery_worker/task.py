from . import celery
from .crawler.crawlerlogger import crawler_logger
from .crawler.logic import fetch_and_store_news  # 你的爬蟲核心
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from models import db, ScheduleState
from time_utils import taipei_now
from datetime import timedelta


@celery.task
def deactivate_inactive_accounts_task():
    from account_activity import deactivate_inactive_users
    from app import create_app

    app = create_app()
    with app.app_context():
        return deactivate_inactive_users()


@celery.task
def hello():
    print("✅ Celery Beat Task: Hello World 每分鐘執行一次！")

@celery.task(bind=True, max_retries=3)
def scheduled_crawl_task(self):
    crawler_logger.info(f"🟡 Celery 任務執行 {taipei_now()}")
    try:
        # 延遲導入 Flask app 避免循環導入
        from app import create_app
        app = create_app()
        
        with app.app_context():
            start_time = taipei_now()
            added = fetch_and_store_news()
            end_time = taipei_now()

            crawler_logger.info(f"🟢 爬蟲新增 {added} 筆資料，耗時 {(end_time - start_time).total_seconds()} 秒")

            now = taipei_now()
            future = now + timedelta(minutes=15)

            state = ScheduleState.query.filter_by(job_name="news_crawler").first()
            if state:
                state.last_run = now
                state.next_run = future
                db.session.commit()
            else:
                crawler_logger.error("找不到 news_crawler 的 ScheduleState")
    except Exception as e:
        crawler_logger.error(f"🔴 Celery 任務錯誤: {e}")
        self.retry(exc=e, countdown=60)  # 有需要可 retry
