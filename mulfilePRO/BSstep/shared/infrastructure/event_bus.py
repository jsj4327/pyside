# shared/infrastructure/event_bus.py
from PySide2.QtCore import QObject, Signal

class EventBus(QObject):
    # 定义全局通用的事件信号，携带字典或任意数据
    event_published = Signal(str, dict)

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EventBus, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        super().__init__()
        self._initialized = True
        self._subscribers = {}

    def publish(self, event_name: str, data: dict = None):
        """发布事件"""
        if data is None:
            data = {}
        # 既可以通过 Qt 信号分发，也可以通过内部回调分发
        self.event_published.emit(event_name, data)
        if event_name in self._subscribers:
            for callback in self._subscribers[event_name]:
                callback(data)

    def subscribe(self, event_name: str, callback):
        """订阅事件"""
        if event_name not in self._subscribers:
            self._subscribers[event_name] = []
        if callback not in self._subscribers[event_name]:
            self._subscribers[event_name].append(callback)

# 全局单例
event_bus = EventBus()