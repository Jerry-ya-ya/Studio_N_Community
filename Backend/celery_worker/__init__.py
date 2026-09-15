from celery import Celery
from celery.schedules import crontab
import os

# 確保環境變數設定正確
from config import DevelopmentConfig, TestingConfig, ProductionConfig

config_map = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}

env = os.getenv("FLASK_ENV", "development").lower()
Config = config_map.get(env, DevelopmentConfig)

celery = Celery(
    'jackandbeanstalks',
    broker=Config.CELERY_BROKER_URL,
    backend=Config.CELERY_RESULT_BACKEND,
    include=['celery_worker.task']  # 包含任務模組
)

# Celery 設定
celery.conf.update(
    timezone='Asia/Taipei',
    enable_utc=False,
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    # Beat 排程設定
    beat_schedule={
        'hello-every-10-mins': {
            'task': 'celery_worker.task.hello',
            'schedule': 600.0
        },
        'crawler-every-15-mins': {
            'task': 'celery_worker.task.scheduled_crawl_task',
            'schedule': crontab(minute='*/15'),  # 每 15 分鐘執行一次
        },
        'deactivate-inactive-users-daily': {
            'task': 'celery_worker.task.deactivate_inactive_accounts_task',
            'schedule': crontab(hour=0, minute=5),
        },
    }
)

# 綁定 Flask context 給 Celery 任務使用
class ContextTask(celery.Task):
    def __call__(self, *args, **kwargs):
        # 延遲導入 Flask app 避免循環導入
        try:
            from flask import current_app
            with current_app.app_context():
                return self.run(*args, **kwargs)
        except RuntimeError:
            # 如果沒有 Flask context，直接執行任務
            return self.run(*args, **kwargs)

celery.Task = ContextTask

# 導出 celery 實例
__all__ = ['celery']
