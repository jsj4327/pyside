# -*- coding: utf-8 -*-
from PySide2.QtCore import QSettings
from config.settings import APP_NAME, ORG_NAME, PROMPT_KEY_PREFIX, DEFAULT_PROMPTS


class PromptManager:
    """Prompt模板的加载、保存、占位符替换逻辑"""

    def __init__(self):
        self.settings = QSettings(ORG_NAME, APP_NAME)

    def load_prompt(self, title):
        key = f"{PROMPT_KEY_PREFIX}{title}"
        default = DEFAULT_PROMPTS.get(title, "")
        return self.settings.value(key, default)

    def save_prompt(self, title, content):
        key = f"{PROMPT_KEY_PREFIX}{title}"
        self.settings.setValue(key, content)

    def save_all(self, editors_map):
        for title, editor in editors_map.items():
            self.save_prompt(title, editor.toPlainText())

    @staticmethod
    def render(template, user_input):
        if "$_$" in template:
            return template.replace("$_$", user_input)
        return f"{template}\n{user_input}"

    def get_default_titles(self):
        return list(DEFAULT_PROMPTS.keys())
