# -*- coding:utf-8 -*-


class PromptBuilder:
    """AI 提示词构建器 - 参照已验证的 prompt 格式"""

    @staticmethod
    def build_initial_prompt(description: str) -> str:
        """
        构建初始项目创建请求
        参照 ai_splitter 中已验证的 prompt 格式
        """
        return f"""请根据以下需求创建完整的项目代码。

【需求描述】
{description}

请按以下JSON格式返回项目文件列表（只返回JSON，不要其他内容）：
[
    {{"path": "相对路径/文件名", "content": "文件完整内容"}}
]

⚠️ 重要：为了确保JSON数据在网页端正确传输，请将JSON字符串中所有下划线 '_' 字符替换为 Unicode 转义序列 '\\u005f'。
示例：'__init__.py' 应写为 '\\u005f\\u005finit\\u005f.py'；'_internal' 应写为 '\\u005finternal'。

请将整个JSON结构放在 ```json 代码块中返回。"""