# -*- coding: utf-8 -*-
"""config.py — 全局配置模块"""
import os

APP_NAME = "AI_Assistant_Pro"
DEFAULT_BASE_URL = "http://paper.people.com.cn/rmrb/pc"
DEFAULT_SAVE_DIR = os.path.join(os.path.expanduser("~"), "CrawledArticles")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

BATCH_SIZE = 50
MAX_LOG_LINES = 500
PAGE_SIZE = 50