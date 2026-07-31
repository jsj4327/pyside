# services/exporter.py
"""
数据多格式导出服务：支持导出 JSON, TXT, CSV 与 Markdown 格式。
"""
import json
import csv
from typing import List, Dict, Any

def export_json(articles: List[Dict[str, Any]], file_path: str):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

def export_txt(articles: List[Dict[str, Any]], file_path: str):
    with open(file_path, "w", encoding="utf-8") as f:
        for article in articles:
            f.write(f"标题：{article.get('title', '')}\n")
            if article.get("subtitle"):
                f.write(f"副标题：{article.get('subtitle')}\n")
            f.write(f"日期：{article.get('date', '')}  版面：{article.get('page_num', '')} {article.get('page_name', '')}\n")
            if article.get("author"):
                f.write(f"作者：{article.get('author')}\n")
            f.write(f"链接：{article.get('url', '')}\n")
            f.write("-" * 50 + "\n")
            f.write(f"{article.get('content', '')}\n")
            f.write("=" * 70 + "\n\n")

def export_csv(articles: List[Dict[str, Any]], file_path: str):
    fieldnames = ["id", "date", "title", "subtitle", "author", "page_num", "page_name", "url", "word_count", "content"]
    with open(file_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(articles)

def export_markdown(articles: List[Dict[str, Any]], file_path: str):
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"# ReadPaper 导出的新闻数据 ({len(articles)} 篇)\n\n")
        for article in articles:
            f.write(f"## {article.get('title', '')}\n\n")
            if article.get("subtitle"):
                f.write(f"> **{article.get('subtitle')}**\n\n")
            f.write(f"- **日期**：`{article.get('date', '')}`\n")
            f.write(f"- **版面**：`{article.get('page_num', '')} {article.get('page_name', '')}`\n")
            f.write(f"- **作者**：{article.get('author', '未知')}\n")
            f.write(f"- **原文链接**：[{article.get('url', '')}]({article.get('url', '')})\n\n")
            f.write("### 正文内容\n\n")
            f.write(f"{article.get('content', '')}\n\n")
            f.write("---\n\n")

def export_single_txt(article: Dict[str, Any], file_path: str):
    export_txt([article], file_path)