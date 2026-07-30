# -*- coding: utf-8 -*-

# -*- coding: utf-8 -*-
"""Agent 外层：Prompt 模板 QSettings 持久化。"""
from typing import Dict, Optional

from PySide2.QtCore import QSettings

from modules.agent.domain.prompt_template import DEFAULT_PROMPTS


class PromptStore:
    def __init__(self, org: str = "AIWorkspace", app: str = "CodeSyncAppRawSave"):
        self._settings = QSettings(org, app)

    def load_all(self, defaults: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        base = dict(defaults or DEFAULT_PROMPTS)
        result = {}
        for title, default_text in base.items():
            result[title] = self._settings.value(f"prompt_{title}", default_text)
        return result

    def save(self, title: str, text: str) -> None:
        self._settings.setValue(f"prompt_{title}", text)

    def save_many(self, prompts: Dict[str, str]) -> None:
        for title, text in prompts.items():
            self.save(title, text)