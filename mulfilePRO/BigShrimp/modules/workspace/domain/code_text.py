# -*- coding: utf-8 -*-

# -*- coding: utf-8 -*-
"""Workspace 内层：代码文本还原。"""


def clean_raw_text(code_text: str) -> str:
    """仅做基础转义还原，保持内容原汁原味。"""
    if not code_text:
        return ""
    return (
        code_text.replace("\\n", "\n")
        .replace("\\t", "\t")
        .replace('\\"', '"')
        .replace("\\\\", "\\")
    )