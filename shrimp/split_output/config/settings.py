# -*- coding: utf-8 -*-
import os

APP_NAME = "CodeSyncAppRawSave"
ORG_NAME = "AIWorkspace"
DEFAULT_PORT = 9002
DEFAULT_SAVE_DIR = os.path.join(os.getcwd(), "output_codes")

PROMPT_KEY_PREFIX = "prompt_"

DEFAULT_PROMPTS = {
    "代码生成助手": """{
  "model": "deepseek-chat",
  "messages": [
    {
      "role": "system",
      "content": "你是一个严谨的代码生成助手。请严格按照以下 JSON 格式输出，不要输出任何 Markdown 标记或额外解释：\\n\\n【核心要求】：\\n1. 代码字段（code）中必须完整保留规范的代码缩进结构。\\n2. 缩进统一使用 4 个空格。\\n3. 代码中的所有换行必须严格转义为 \\\\n，确保整个 JSON 结构合法且可被直接解析。\\n\\n【输出格式】：\\n{\\n  \\\"files\\\": [\\n    {\\n      \\\"filename\\\": \\\"文件名1.py\\\",\\n      \\\"code\\\": \\\"def foo():\\\\n    print('Hello World')\\\"\\n    }\\n  ]\\n}"
    },
    {
      "role": "user",
      "content": "$_$"
    }
  ],
  "response_format": {
    "type": "json_object"
  },
  "temperature": 0.1
}"""
}
