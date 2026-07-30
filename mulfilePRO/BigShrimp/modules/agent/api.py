# -*- coding: utf-8 -*-
"""Agent 模块对外 API（本阶段：Prompt 组装与持久化）。"""
from typing import Dict, Optional

from modules.agent.application.handle_user_message import build_extension_command
from modules.agent.domain.prompt_template import DEFAULT_PROMPTS
from modules.agent.infrastructure.persistence.prompt_store import PromptStore


class AgentApi:
    def __init__(self, store: Optional[PromptStore] = None):
        self._store = store or PromptStore()
        self._prompts: Dict[str, str] = self._store.load_all(DEFAULT_PROMPTS)

    @property
    def prompts(self) -> Dict[str, str]:
        return self._prompts

    def get_prompt(self, title: str) -> str:
        return self._prompts.get(title, "")

    def set_prompt(self, title: str, text: str, persist: bool = True) -> None:
        self._prompts[title] = text
        if persist:
            self._store.save(title, text)

    def persist_all(self) -> None:
        self._store.save_many(self._prompts)

    def build_command(self, scene_title: str, user_input: str) -> str:
        template = self.get_prompt(scene_title)
        return build_extension_command(template, user_input)