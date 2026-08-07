# -*- coding:utf-8 -*-
import os
from typing import List, Optional


class FeedbackBuilder:
    """反馈信息打包器"""
    
    def __init__(self, parent=None):
        self.parent = parent
    
    def build_feedback(self,
                       file_path: str,
                       stdout: str,
                       stderr: str,
                       exit_code: int,
                       template: str = None,
                       context: str = None) -> str:
        """
        打包反馈信息
        
        Args:
            file_path: 执行的文件路径
            stdout: 标准输出
            stderr: 标准错误
            exit_code: 退出码
            template: 模板内容（可选）
            context: 上下文信息（可选）
        
        Returns:
            格式化后的反馈文本
        """
        print(f"[FEEDBACK] 打包反馈: {file_path}")
        
        parts = []
        
        # 1. 文件信息
        parts.append("=" * 60)
        parts.append("【调试执行反馈】")
        parts.append("=" * 60)
        parts.append("")
        
        filename = os.path.basename(file_path) if file_path else "未知文件"
        parts.append(f"📄 文件: {filename}")
        parts.append(f"📁 路径: {file_path}")
        parts.append(f"🔢 退出码: {exit_code}")
        
        # 读取文件内容
        file_content = self._read_file_content(file_path)
        if file_content:
            parts.append(f"📝 文件大小: {len(file_content)} 字符")
        parts.append("")
        
        # 2. 上下文信息
        if context:
            parts.append("【上下文信息】")
            parts.append(context)
            parts.append("")
        
        # 3. 标准输出（如果有）
        if stdout and stdout.strip():
            parts.append("【标准输出】")
            parts.append("```")
            parts.append(stdout.rstrip())
            parts.append("```")
            parts.append("")
        
        # 4. 标准错误（如果有）
        if stderr and stderr.strip():
            parts.append("【错误输出】")
            parts.append("```")
            parts.append(stderr.rstrip())
            parts.append("```")
            parts.append("")
        else:
            parts.append("✅ 没有错误输出")
            parts.append("")
        
        # 5. 文件内容（如果有错误）
        if exit_code != 0 and file_content:
            parts.append("【文件完整内容】")
            parts.append("```python")
            parts.append(file_content)
            parts.append("```")
            parts.append("")
        
        # 6. 应用模板
        if template:
            parts.append("=" * 60)
            parts.append("【分析要求】")
            parts.append("=" * 60)
            
            # 填充模板
            filled_template = self._apply_template(template, file_path, stdout, stderr, exit_code, file_content)
            parts.append(filled_template)
        
        parts.append("")
        parts.append("请分析以上错误并提供修复建议。")
        
        return "\n".join(parts)
    
    def _read_file_content(self, file_path: str) -> Optional[str]:
        """读取文件内容"""
        if not file_path or not os.path.exists(file_path):
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"[FEEDBACK] 读取文件失败: {e}")
            return None
    
    def _apply_template(self, 
                        template: str, 
                        file_path: str,
                        stdout: str,
                        stderr: str,
                        exit_code: int,
                        file_content: str) -> str:
        """应用模板"""
        try:
            # 准备模板变量
            context_data = {
                'file_path': file_path,
                'file_name': os.path.basename(file_path) if file_path else "",
                'exit_code': exit_code,
                'stdout': stdout[:1000] if stdout else "",  # 限制长度
                'stderr': stderr[:1000] if stderr else "",
                'file_content': file_content[:5000] if file_content else "",  # 限制长度
                'has_error': "是" if exit_code != 0 else "否"
            }
            
            # 尝试填充模板
            return template.format(**context_data)
        except KeyError as e:
            print(f"[FEEDBACK] 模板填充失败 (缺少变量 {e})，使用原始模板")
            return template
        except Exception as e:
            print(f"[FEEDBACK] 模板填充失败: {e}")
            return template + f"\n\n【错误信息】\n{stderr}" if stderr else template
    
    def build_simple_feedback(self, file_path: str, error_msg: str) -> str:
        """构建简单的反馈（用于快速反馈）"""
        parts = []
        parts.append("【调试错误反馈】")
        parts.append("")
        parts.append(f"文件: {file_path}")
        parts.append("")
        parts.append("错误信息:")
        parts.append("```")
        parts.append(error_msg)
        parts.append("```")
        parts.append("")
        parts.append("请分析以上错误并提供修复建议。")
        return "\n".join(parts)