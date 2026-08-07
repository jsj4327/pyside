# -*- coding:utf-8 -*-
import socket


def validate_port(port: int) -> bool:
    """验证端口是否有效"""
    return 1024 <= port <= 65535


def get_local_ip() -> str:
    """获取本机 IP 地址"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"