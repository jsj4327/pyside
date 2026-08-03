# modules/shell/application/shell_controller.py
from shared.infrastructure.event_bus import event_bus


class ShellController:
    """Shell 模块的应用层控制器，负责业务逻辑、状态管理与事件编排"""

    def __init__(self, view=None):
        self.view = view
        event_bus.subscribe("request:result_ready", self.handle_result_ready)
        event_bus.subscribe("bridge:server_status", self.handle_server_status)
        event_bus.subscribe("bridge:client_status", self.handle_client_status)
        event_bus.subscribe("plugin:data_processed", self.handle_plugin_data_processed)
        event_bus.subscribe("workspace:scan_finished", self.handle_workspace_scan_finished)
        # 新增：订阅处理进度事件
        event_bus.subscribe("request:progress", self.handle_progress)

    def handle_send_request(self, raw_text: str, framework: str):
        print(f"[ShellController] 触发请求发送，当前框架: {framework}")
        event_bus.publish("request:send_clicked", {
            "raw_prompt": raw_text,
            "framework": framework
        })

    def handle_framework_change(self, framework_name: str):
        event_bus.publish("framework:changed", {"framework": framework_name})

    def handle_result_ready(self, data: dict):
        final_prompt = data.get("final_prompt", "")
        parsed_result = data.get("parsed_result", "")

        if self.view:
            self.view.update_results(final_prompt, parsed_result)

        if final_prompt and final_prompt.strip():
            event_bus.publish("bridge:send_to_extension", {"text": final_prompt})
            print("[ShellController] 最终提示词校验通过，已向插件端口发送")
        else:
            print("[ShellController] 最终提示词为空，已拦截，不向插件发送")

    def handle_server_status(self, data: dict):
        is_running = data.get("is_running", False)
        port = data.get("port", 9002)
        if self.view:
            self.view.update_server_status(is_running, port, data.get("error", ""))

    def handle_client_status(self, data: dict):
        state = data.get("state", "init")
        if self.view:
            self.view.update_client_status(state)

    def handle_plugin_data_processed(self, data: dict):
        raw_result = data.get("raw_result", "")
        parsed_result = data.get("parsed_result", "")

        if self.view:
            self.view.update_plugin_received_results(raw_result, parsed_result)
        print("[ShellController] 已将插件数据更新至反馈结果与结果解析控件")

    def request_scan_workspace(self, dir_path: str, exclude_exts: str, exclude_empty: bool):
        """发起文件夹扫描请求"""
        print(f"[ShellController] 触发工作台扫描: {dir_path}, 过滤空文件: {exclude_empty}")
        event_bus.publish("workspace:scan_requested", {
            "dir_path": dir_path,
            "exclude_exts": exclude_exts,
            "exclude_empty": exclude_empty
        })

    def handle_workspace_scan_finished(self, data: dict):
        success = data.get("success", False)
        message = data.get("message", "")
        file_list = data.get("file_list", [])

        if self.view:
            self.view.update_workspace_scanned_files(success, message, file_list)
        print(f"[ShellController] 工作台扫描结果已同步至视图: {message}")

    # ========================================
    # 新增：进度处理
    # ========================================

    def handle_progress(self, data: dict):
        """更新处理进度"""
        if self.view and hasattr(self.view, 'update_progress'):
            percent = data.get("percent", 0)
            status = data.get("status", "处理中...")
            self.view.update_progress(percent, status)
        else:
            # 降级处理：直接打印
            print(f"[Progress] {data.get('status', '')} ({data.get('percent', 0)}%)")