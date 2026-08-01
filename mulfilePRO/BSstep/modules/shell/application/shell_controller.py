# modules/shell/application/shell_controller.py
from shared.infrastructure.event_bus import event_bus

class ShellController:
    """Shell 模块的应用层控制器，负责业务逻辑、状态管理与事件编排"""

    def __init__(self, view=None):
        self.view = view
        # 订阅全局系统事件
        event_bus.subscribe("request:result_ready", self.handle_result_ready)
        event_bus.subscribe("bridge:server_status", self.handle_server_status)
        event_bus.subscribe("bridge:client_status", self.handle_client_status)

    def handle_send_request(self, raw_text: str, framework: str):
        """处理用户点击发送请求的业务逻辑"""
        print(f"[ShellController] 触发请求发送，当前框架: {framework}")
        event_bus.publish("request:send_clicked", {
            "raw_prompt": raw_text,
            "framework": framework
        })

    def handle_framework_change(self, framework_name: str):
        """处理框架切换的业务逻辑"""
        event_bus.publish("framework:changed", {"framework": framework_name})

    def handle_result_ready(self, data: dict):
        """处理 Agent 返回结果：校验最终提示词并决定是否推送给插件端"""
        final_prompt = data.get("final_prompt", "")
        parsed_result = data.get("parsed_result", "")

        # 通知视图渲染数据
        if self.view:
            self.view.update_results(final_prompt, parsed_result)

        # 业务规则：校验最终提示词是否为空，决定是否通过桥接通道推送给插件端
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