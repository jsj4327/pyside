# modules/agent/infrastructure/prompt_engine.py
# -*- coding: utf-8 -*-

from shared.infrastructure.event_bus import event_bus


class AgentEngineService:
    def __init__(self):
        # 订阅 UI 层的事件
        event_bus.subscribe("request:send_clicked", self.handle_request)
        event_bus.subscribe("framework:changed", self.handle_framework_change)

    def handle_framework_change(self, data: dict):
        framework = data.get("framework", "")
        # 后续可在此对接具体的提示词模板加载逻辑
        print(f"[AgentEngine] 加载框架模板: {framework}")
        
        # 发布进度事件（框架加载）
        event_bus.publish("request:progress", {
            "percent": 20,
            "status": f"已加载框架: {framework}"
        })

    def handle_request(self, data: dict):
        raw_prompt = data.get("raw_prompt", "")
        framework = data.get("framework", "")
        
        # 发布进度：开始
        event_bus.publish("request:progress", {
            "percent": 10,
            "status": "正在加载框架..."
        })

        # 模拟框架加载
        event_bus.publish("request:progress", {
            "percent": 30,
            "status": "正在构建提示词..."
        })

        # 模拟 AI 提示词组装与沙箱/大模型预处理逻辑
        final_prompt = f"--- [AI 提示词工程引擎] ---\n框架类型: {framework}\n原始内容:\n{raw_prompt}\n---------------------------"

        event_bus.publish("request:progress", {
            "percent": 60,
            "status": "正在解析结果..."
        })

        parsed_result = f"请求已成功由 Agent 核心处理。\n- 字符数: {len(raw_prompt)}\n- 状态: 就绪，等待大模型网关响应..."

        event_bus.publish("request:progress", {
            "percent": 90,
            "status": "准备发送至插件..."
        })

        # 异步处理完成后，通过事件总线将结果发布回传给 UI
        event_bus.publish("request:result_ready", {
            "final_prompt": final_prompt,
            "parsed_result": parsed_result
        })

        event_bus.publish("request:progress", {
            "percent": 100,
            "status": "处理完成"
        })

        print(f"[AgentEngine] 请求处理完成，已发布 result_ready 事件")


# 创建单例实例以保证生命周期存活并完成事件监听注册
agent_engine_service = AgentEngineService()