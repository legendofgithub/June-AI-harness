"""
统一响应格式 —— 参照 AgentX 的 Result<T> 模式，
但简化：不设泛型，直接返回 dict。

格式：{"code": 200, "message": "操作成功", "data": {...}, "timestamp": 1718000000}
"""
import time


def success(data=None, message: str = "操作成功") -> dict:
    return {
        "code": 200,
        "message": message,
        "data": data,
        "timestamp": int(time.time() * 1000),
    }


def error(code: int, message: str, data=None) -> dict:
    return {
        "code": code,
        "message": message,
        "data": data,
        "timestamp": int(time.time() * 1000),
    }


def bad_request(message: str = "请求参数错误") -> dict:
    return error(400, message)


def unauthorized(message: str = "未授权") -> dict:
    return error(401, message)


def not_found(message: str = "资源不存在") -> dict:
    return error(404, message)


def server_error(message: str = "服务器内部错误") -> dict:
    return error(500, message)
