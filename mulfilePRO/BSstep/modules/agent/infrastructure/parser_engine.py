from shared.infrastructure.event_bus import event_bus

class ParserEngineService:
    def __init__(self):
        # 监听来自 WebSocket 桥接接收到的插件数据
        event_bus.subscribe("bridge:message_received", self.handle_plugin_message)

    def dummy_parse_rule(self, raw_payload: dict) -> str:
        """
        空函数解析规则：直接透传。
        后续您可以在这里编写复杂的解析逻辑，将字典转为特定格式的字符串。
        """
        return str(raw_payload)

    def handle_plugin_message(self, data):
        """处理插件发来的数据，执行解析规则，并通过事件回传给 Shell 层"""
        print(f"[ParserEngine] 收到插件下发数据: {data}")
        
        # 兼容处理：如果发来的是字符串，直接作为 payload；如果是字典，按字典取值
        if isinstance(data, dict):
            payload = data.get("payload", data)
        else:
            payload = data
        
        # 模拟“反馈结果”
        raw_result_str = f"收到插件回传数据\n数据内容: {str(payload)}"
        
        # 使用空函数解析规则进行透传
        parsed_result_str = self.dummy_parse_rule(payload)

        # 通过事件总线将处理后的结果分发给 UI
        event_bus.publish("plugin:data_processed", {
            "raw_result": raw_result_str,
            "parsed_result": parsed_result_str
        })

# 【关键补充】创建单例实例以保证生命周期存活并完成事件监听注册
parser_engine_service = ParserEngineService()