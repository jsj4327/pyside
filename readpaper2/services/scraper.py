# services/scraper.py
"""
网络抓取策略模块：包含 User-Agent 随机轮询、自动指数退避重试与链接生成。
"""
import random
import time
import requests
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from config import USER_AGENTS, DEFAULT_TIMEOUT, MAX_RETRIES, RETRY_DELAY, DEFAULT_BASE_URL

logger = logging.getLogger(__name__)

def fetch_page(url: str, retries: int = MAX_RETRIES, timeout: int = DEFAULT_TIMEOUT) -> Optional[str]:
    session = requests.Session()
    for attempt in range(1, retries + 1):
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        try:
            response = session.get(url, headers=headers, timeout=timeout)
            response.encoding = "utf-8"
            if response.status_code == 200:
                return response.text
            elif response.status_code == 404:
                logger.debug(f"页面不存在 (404): {url}")
                return None
            else:
                logger.warning(f"请求返回非200状态码 [{response.status_code}], 正在重试 ({attempt}/{retries}): {url}")
        except requests.RequestException as e:
            logger.warning(f"网络异常 [{str(e)}], 正在重试 ({attempt}/{retries}): {url}")
        time.sleep(RETRY_DELAY * attempt)
    return None

def generate_layout_urls(start_date: str, end_date: str, base_url: str = DEFAULT_BASE_URL) -> List[str]:
    urls = []
    try:
        dt_start = datetime.strptime(start_date, "%Y-%m-%d")
        dt_end = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError as e:
        logger.error(f"日期格式不正确, 正确格式应为 YYYY-MM-DD: {str(e)}")
        return urls

    curr = dt_start
    while curr <= dt_end:
        date_str = curr.strftime("%Y-%m/%d")
        for page in range(1, 21):  # 人民日报一般每天最大 20 个版面
            page_str = f"node_{page:02d}.htm" if page > 1 else "nbs.D110000renmrb_01.htm"
            url = f"{base_url}/{date_str}/{page_str}"
            urls.append(url)
        curr += timedelta(days=1)

    return urls