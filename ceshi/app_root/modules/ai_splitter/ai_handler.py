# -*- coding:utf-8 -*-
import os
import json
import re
from PySide2.QtWidgets import QMessageBox


class AIHandlerMixin:
    """AI 交互核心逻辑（Mixin）"""

    # ---------- 辅助：从响应中提取 JSON（支持多种格式） ----------
    def _extract_json_from_response(self, text):
        """
        从 AI 响应中提取 JSON，支持多种格式：
        - Markdown 代码块 (```json ... ```)
        - 带汉字包裹标记（如 【代码块 json】...【代码块结束】）
        - 纯文本 JSON（直接解析）
        - 自动去除行号前缀（如 "1 {", "2 \"type\":"）
        - 自动去除前后多余的文字（只要找到有效的 JSON 结构）
        """
        if not text:
            return None

        # 步骤 0：定义去除行号函数
        def strip_line_numbers(content):
            lines = content.splitlines()
            stripped_lines = []
            for line in lines:
                # 去除行首的数字（可能带点、括号等）和后续空格
                stripped = re.sub(r'^\s*\d+[\.\)]?\s*', '', line)
                stripped_lines.append(stripped)
            return '\n'.join(stripped_lines)

        # 步骤 1：提取所有可能被包裹的内容
        candidates = []

        # 1.1 从 ```json ... ``` 代码块提取
        match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
        if match:
            candidates.append(match.group(1).strip())

        # 1.2 从 ``` ... ``` 代码块（无语言标识）提取
        match = re.search(r'```\s*([\s\S]*?)\s*```', text)
        if match:
            candidates.append(match.group(1).strip())

        # 1.3 从 【代码块 json】...【代码块结束】 等汉字标记中提取
        # 匹配各种可能的标记：代码块 json、json、JSON、结果等
        match = re.search(r'【?[\u4e00-\u9fa5]*\s*(?:json|JSON|代码块|结果)\s*】?\s*([\s\S]*?)\s*【?[\u4e00-\u9fa5]*\s*(?:结束|结尾|完毕)\s*】?', text)
        if match:
            candidates.append(match.group(1).strip())

        # 1.4 直接提取整个文本（作为最后候选）
        candidates.append(text.strip())

        # 步骤 2：遍历候选，尝试解析
        for raw_candidate in candidates:
            # 先去除可能的前后非 JSON 文字：找到第一个 { 或 [，到最后一个 } 或 ]
            # 但如果候选内容中同时包含 { 和 }，则提取区间
            # 更健壮：使用正则提取 JSON 对象或数组
            # 先尝试直接清理行号后解析
            cleaned = strip_line_numbers(raw_candidate)
            # 新增：将 \u005f 替换为 _，兼容 AI 响应中的转义
            cleaned = cleaned.replace('\\u005f', '_')

            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                pass

            # 如果失败，尝试在清理后的文本中提取 JSON 片段（最宽松）
            # 匹配 JSON 对象或数组
            json_match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', cleaned)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass

            # 如果还是失败，尝试在原候选（不清理行号）中提取 JSON 片段（可能 AI 在行号外还有额外文字）
            # 但我们已经清理过，通常已足够

        # 步骤 3：如果以上都失败，尝试从整个原始文本中暴力提取 JSON
        # 在某些极端情况下，AI 可能根本没给出代码块或标记，但文本中包含 JSON
        # 使用正则提取最外层 JSON 对象
        json_match = re.search(r'(\{[\s\S]*\})', text)
        if json_match:
            try:
                candidate = json_match.group(1)
                cleaned = strip_line_numbers(candidate)
                cleaned = cleaned.replace('\\u005f', '_')   # 新增
                return json.loads(cleaned)
            except json.JSONDecodeError:
                pass

        # 所有尝试均失败，返回 None
        return None

    # ---------- 发送给 AI ----------
    def _send_to_ai(self, message):
        main_win = self.window()
        if not main_win or not hasattr(main_win, 'bridge_server'):
            QMessageBox.critical(self, "错误", "Bridge 服务未启动")
            return
        bridge = main_win.bridge_server
        if not bridge.clients:
            QMessageBox.warning(self, "警告", "没有插件客户端连接")
            return

        payload = {
            "type": "ANALYZE_REQUEST",
            "filename": "ai_request",
            "content": message,
            "message": "AI 拆分助手请求"
        }
        bridge.send_to_all_clients(payload)

    # ---------- 接收 AI 响应 ----------
    def append_ai_result(self, result_text):
        if not result_text:
            return

        if self.stage == 'plan_requested':
            self._handle_plan_response(result_text)
        elif self.stage == 'data_requested':
            self._handle_data_response(result_text)
        else:
            self.log_text.append("⚠️ 未处于等待状态，忽略响应")

    # ---------- 处理方案响应 ----------
    def _handle_plan_response(self, text):
        data = self._extract_json_from_response(text)

        if data and isinstance(data, dict) and data.get('type') == 'plan':
            self.plan_data = data
            self.log_text.append("✅ 重构方案解析成功")
            desc = data.get('plan_description', '')
            structure = data.get('file_structure', [])
            self.log_text.append(f"  方案描述: {desc}")
            self.log_text.append(f"  预计生成 {len(structure)} 个文件")
            self.stage = 'plan_received'
            self._request_data()
        else:
            self.log_text.append("⚠️ 未能提取有效的方案JSON，请检查AI响应格式")
            self._reset_analyze_button()

    # ---------- 处理文件数据响应 ----------
    def _handle_data_response(self, text):
        data = self._extract_json_from_response(text)

        if data and isinstance(data, dict) and data.get('type') == 'files':
            files = data.get('files', [])
            if files:
                self._response_chunks.extend(files)
                self.log_text.append(f"✅ 收到第 {self.current_chunk_index+1} 批文件列表，共 {len(files)} 个文件")
            else:
                self.log_text.append("⚠️ 返回的文件列表为空")
        else:
            self.log_text.append("⚠️ 未能提取有效的文件数据JSON，请检查AI响应格式")

        self.current_chunk_index += 1
        if self.current_chunk_index < len(self._chunks):
            self._send_chunk()
        else:
            self.progress_bar.setVisible(False)
            self._merge_and_save()

    # ---------- 合并保存 ----------
    def _merge_and_save(self):
        if not self._response_chunks:
            self.log_text.append("⚠️ 没有收到任何有效的文件数据")
            self._reset_analyze_button()
            return

        file_map = {}
        for item in self._response_chunks:
            if isinstance(item, dict) and 'path' in item and 'content' in item:
                file_map[item['path']] = item['content']
        if not file_map:
            self.log_text.append("⚠️ 没有有效的文件条目")
            self._reset_analyze_button()
            return

        target_dir = self._target_dir
        if not target_dir:
            target_dir = self.target_dir_edit.text().strip()
        if not target_dir:
            self.log_text.append("⚠️ 目标目录未设置")
            self._reset_analyze_button()
            return

        success = 0
        for rel_path, content in file_map.items():
            full_path = os.path.join(target_dir, rel_path)
            dir_name = os.path.dirname(full_path)
            try:
                if dir_name and not os.path.exists(dir_name):
                    os.makedirs(dir_name)
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                success += 1
                self.log_text.append(f"✅ 创建文件: {rel_path}")
            except Exception as e:
                self.log_text.append(f"❌ 创建文件 {rel_path} 失败: {e}")

        self.log_text.append(f"🎉 拆分完成！共创建 {success} 个文件，保存于 {target_dir}")
        QMessageBox.information(self, "完成", f"成功拆分并保存 {success} 个文件到目标目录。")
        self.stage = 'data_received'
        self._reset_analyze_button()

    def _reset_analyze_button(self):
        self.btn_analyze.setEnabled(True)

    # ---------- Token 估算 ----------
    def estimate_tokens(self, text):
        try:
            import tiktoken
            enc = tiktoken.get_encoding("cl100k_base")
            return len(enc.encode(text, disallowed_special=()))
        except:
            pass
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        other_chars = len(text) - chinese_chars
        return int(chinese_chars / 1.5 + other_chars / 4)