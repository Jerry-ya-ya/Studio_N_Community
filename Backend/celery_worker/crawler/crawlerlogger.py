from flask import Blueprint
from log_writer import get_backend_logger

crawlerlogger_bp = Blueprint('crawlerlogger_bp', __name__)

crawler_logger = get_backend_logger('crawler', 'crawler.log')
