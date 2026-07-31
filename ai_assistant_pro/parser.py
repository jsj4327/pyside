# -*- coding: utf-8 -*-
"""parser.py — 网页抓取与 BeautifulSoup 解析工具模块"""

from datetime import datetime
import re
import time
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import requests

from config import USER_AGENT


def fetch_page(url, retries=2, cancel_checker=None):
    headers = {"User-Agent": USER_AGENT}
    for attempt in range(retries + 1):
        if cancel_checker and cancel_checker():
            return None
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            if resp.encoding and resp.encoding.lower() == "iso-8859-1":
                resp.encoding = resp.apparent_encoding
            return resp.text
        except requests.RequestException:
            if attempt < retries:
                time.sleep(1)
            else:
                return None
    return None


def generate_urls_from_template(template, p1_cfg=None, p2_cfg=None):
    """根据 URL 模板及最多 2 个占位符范围生成 URL 列表

    p1_cfg / p2_cfg 结构: {'enabled': True, 'start': 1, 'end': 31, 'pad': 2}
    """
    urls = []
    if not template:
        return urls

    p1_enabled = p1_cfg.get("enabled", False) if p1_cfg else False
    p2_enabled = p2_cfg.get("enabled", False) if p2_cfg else False

    p1_start = p1_cfg.get("start", 1) if p1_enabled else 0
    p1_end = p1_cfg.get("end", 1) if p1_enabled else 0
    p1_pad = p1_cfg.get("pad", 1) if p1_enabled else 0

    p2_start = p2_cfg.get("start", 1) if p2_enabled else 0
    p2_end = p2_cfg.get("end", 1) if p2_enabled else 0
    p2_pad = p2_cfg.get("pad", 1) if p2_enabled else 0

    # 未启用任何占位符
    if not p1_enabled and not p2_enabled:
        return [template]

    # 仅启用占位符 1
    if p1_enabled and not p2_enabled:
        for v1 in range(p1_start, p1_end + 1):
            s1 = str(v1).zfill(p1_pad)
            try:
                urls.append(template.format(s1, ""))
            except Exception:
                try:
                    urls.append(template.format(s1))
                except Exception:
                    urls.append(template)

    # 仅启用占位符 2
    elif not p1_enabled and p2_enabled:
        for v2 in range(p2_start, p2_end + 1):
            s2 = str(v2).zfill(p2_pad)
            try:
                urls.append(template.format("", s2))
            except Exception:
                try:
                    urls.append(template.format(s2))
                except Exception:
                    urls.append(template)

    # 两个占位符均启用（双重循环交错生成）
    else:
        for v1 in range(p1_start, p1_end + 1):
            s1 = str(v1).zfill(p1_pad)
            for v2 in range(p2_start, p2_end + 1):
                s2 = str(v2).zfill(p2_pad)
                try:
                    urls.append(template.format(s1, s2))
                except Exception:
                    pass

    return urls


def extract_date_from_layout_url(url):
    """正则匹配提取 URL 中的日期，如 /202607/31/ -> 2026-07-31"""
    m = re.search(r"(\d{4})[/-]?(\d{2})[/-]?(\d{2})", url)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return datetime.now().strftime("%Y-%m-%d")


def parse_layout_page(html, layout_url, layout_date):
    soup = BeautifulSoup(html, "html.parser")
    articles = []
    section_name = "未知版面"

    title_tag = soup.find("title")
    if title_tag:
        section_name = title_tag.get_text(strip=True).split("-")[0].strip()

    links = soup.select("div.news ul.news-list li a[href]") or soup.select(
        "ul li a[href]"
    )
    for a in links:
        title = a.get_text(strip=True)
        href = a.get("href", "")
        if not title or not href or len(title) < 4:
            continue
        full_url = urljoin(layout_url, href)
        if "content" not in full_url and "article" not in full_url:
            continue

        articles.append(
            {
                "title": title,
                "url": full_url,
                "subtitle": "",
                "author": "",
                "date": layout_date,
                "section": section_name,
                "source": urlparse(full_url).netloc,
                "content": "",
            }
        )
    return articles


def parse_article_page(html):
    soup = BeautifulSoup(html, "html.parser")
    result = {}

    h1 = soup.select_one("div.article h1") or soup.find("h1")
    result["title"] = h1.get_text(strip=True) if h1 else ""

    h3 = soup.select_one("div.article h3")
    result["subtitle"] = h3.get_text(strip=True) if h3 else ""

    sec_p = soup.select_one("p.sec")
    if sec_p:
        sec_text = sec_p.get_text(strip=True)
        result["author"] = re.sub(r"《人民日报》.*$", "", sec_text).strip()
        date_span = sec_p.select_one("span.newstime")
        if date_span:
            result["date"] = date_span.get_text(strip=True)
        else:
            dm = re.search(r"(\d{4})年(\d{2})月(\d{2})日", sec_text)
            result["date"] = (
                f"{dm.group(1)}-{dm.group(2)}-{dm.group(3)}" if dm else ""
            )
    else:
        result["author"] = ""

    body_tag = soup.find("body")
    if body_tag:
        paras = [
            p.get_text(strip=True)
            for p in body_tag.find_all("p")
            if "sec" not in (p.get("class") or []) and p.get_text(strip=True)
        ]
        result["content"] = "\n\n".join(paras)
    else:
        result["content"] = ""

    return result