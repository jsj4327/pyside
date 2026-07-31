# services/parser.py
"""
HTML 结构解析器：基于 BeautifulSoup4 抽取版面与文章字段。
"""
import re
import logging
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def extract_date_from_layout_url(url: str) -> str:
    match = re.search(r"(\d{4}-\d{2}/\d{2})", url)
    if match:
        return match.group(1).replace("/", "-")
    match2 = re.search(r"(\d{4})(\d{2})(\d{2})", url)
    if match2:
        return f"{match2.group(1)}-{match2.group(2)}-{match2.group(3)}"
    return ""

def parse_layout_page(html_content: str, base_url: str) -> List[Dict[str, Any]]:
    if not html_content:
        return []
    soup = BeautifulSoup(html_content, "html.parser")
    articles = []

    page_num = ""
    page_name = ""
    
    # 支持多种选择器降级匹配
    page_info = soup.find("div", class_="page-num") or soup.find("span", class_="name") or soup.find("div", id="pageList")
    if page_info:
        info_text = page_info.get_text(strip=True)
        parts = info_text.split()
        if len(parts) >= 1:
            page_num = parts[0]
        if len(parts) >= 2:
            page_name = parts[1]

    link_list = soup.find_all("a", href=True)
    for a in link_list:
        href = a["href"]
        if "nw.D110000renmrb_" in href or "content_" in href:
            full_url = urljoin(base_url, href)
            title = a.get_text(strip=True)
            if title and len(title) > 1 and not title.startswith("图片"):
                date_str = extract_date_from_layout_url(base_url)
                articles.append({
                    "title": title,
                    "url": full_url,
                    "date": date_str,
                    "page_num": page_num,
                    "page_name": page_name
                })
    return articles

def parse_article_page(html_content: str) -> Dict[str, Any]:
    if not html_content:
        return {"subtitle": "", "author": "", "content": ""}

    soup = BeautifulSoup(html_content, "html.parser")
    
    subtitle = ""
    author = ""
    content_lines = []

    # 尝试提取副标题
    sub_node = soup.find("h3") or soup.find("h2", class_="subtitle") or soup.find("div", class_="sub")
    if sub_node:
        subtitle = sub_node.get_text(strip=True)

    # 尝试提取作者
    author_node = soup.find("p", class_="author") or soup.find("span", class_="author") or soup.find("div", class_="sec-author")
    if author_node:
        author = author_node.get_text(strip=True)

    # 尝试提取正文段落
    content_node = soup.find("div", id="oContent") or soup.find("div", class_="article-content") or soup.find("div", class_="rm_txt_con")
    if content_node:
        paragraphs = content_node.find_all("p")
        for p in paragraphs:
            text = p.get_text(strip=True)
            if text:
                content_lines.append(text)

    return {
        "subtitle": subtitle,
        "author": author,
        "content": "\n\n".join(content_lines)
    }