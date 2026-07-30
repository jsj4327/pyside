# -*- coding: utf-8 -*-
"""用例：根据场景模板组装下发给插件的内容。"""
from modules.agent.domain.prompt_template import assemble_prompt


def build_extension_command(template: str, user_input: str) -> str:
    user_input = (user_input or "").strip()
    if not user_input:
        return ""
    return assemble_prompt(template, user_input)