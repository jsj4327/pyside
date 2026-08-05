# -*- coding:utf-8 -*-


class PromptBuilder:
    """AI 提示词构建器"""

    @staticmethod
    def _base_instruction() -> str:
        """基础指令模板"""
        return f"""⚠️ 强制要求：
1. 不要进行深度思考，直接返回JSON结果。
2. 只返回JSON数组，不要包含任何其他文字。
3. 所有路径中的下划线 '_' 必须替换为 '\\u005f'。

示例：'__init__.py' 应写为 '\\u005f\\u005finit\\u005f.py'；'_internal' 应写为 '\\u005finternal'。
违反此规则会导致程序解析失败！"""

    @staticmethod
    def build_initial_prompt(description: str) -> str:
        """构建初始项目创建请求"""
        return f"""你是一个专业的软件架构师。请根据以下需求创建完整项目。

【描述】{description}

{PromptBuilder._base_instruction()}

请直接返回JSON数组，格式如下：
[
    {{"path": "相对路径/文件名", "content": "完整文件内容"}}
]"""