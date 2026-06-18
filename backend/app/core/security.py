"""
API Token 鉴权中间件 —— Bearer Token 模式。

- 首次启动时，若未配置 JUNE_API_TOKEN 则自动生成并写入 .env
- /health、/、/docs、/openapi.json 等路径免鉴权
- 生产模式下前端通过 localStorage 存储 token，所有 /api/ 请求携带 Authorization: Bearer <token>
- SSE 请求因 EventSource 不支持自定义 Header，token 通过 URL 参数 ?token=xxx 传递
"""
import secrets
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from .config import settings


# 免鉴权路径前缀
PUBLIC_PATHS = {"/health", "/", "/docs", "/openapi.json", "/redoc"}


def _is_public_path(path: str) -> bool:
    """判断路径是否需要跳过鉴权"""
    # 精确匹配
    if path in PUBLIC_PATHS:
        return True
    # /assets/ 下的静态文件
    if path.startswith("/assets/"):
        return True
    # 前端 SPA 页面（非 /api/ 路径）
    if not path.startswith("/api/"):
        return True
    return False


def generate_token() -> str:
    """生成 32 字符的随机 hex token"""
    return secrets.token_hex(32)


def ensure_token() -> str:
    """确保 token 存在：开发模式自动生成，生产模式使用配置值"""
    token = settings.JUNE_API_TOKEN
    if not token:
        token = generate_token()
        # 尝试写入 .env 文件以便重启后保持一致
        _persist_token(token)
        settings.JUNE_API_TOKEN = token
        print(f"\n{'='*60}")
        print(f"[June] 已自动生成 API Token: {token}")
        print(f"[June] 前端首次使用时需要输入此 Token")
        print(f"[June] Token 已保存到 .env 文件")
        print(f"{'='*60}\n")
    return token


def _persist_token(token: str) -> None:
    """将 token 写回 .env 文件（追加或更新）"""
    import os
    from pathlib import Path

    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    try:
        if env_path.exists():
            content = env_path.read_text(encoding="utf-8")
            if "JUNE_API_TOKEN=" in content:
                # 更新已有行
                lines = content.split("\n")
                new_lines = []
                for line in lines:
                    if line.startswith("JUNE_API_TOKEN="):
                        new_lines.append(f"JUNE_API_TOKEN={token}")
                    else:
                        new_lines.append(line)
                env_path.write_text("\n".join(new_lines), encoding="utf-8")
            else:
                # 追加
                with open(env_path, "a", encoding="utf-8") as f:
                    f.write(f"\nJUNE_API_TOKEN={token}\n")
        else:
            env_path.write_text(f"JUNE_API_TOKEN={token}\n", encoding="utf-8")
    except Exception:
        pass  # 写入失败不影响运行，token 在内存中仍然有效


class TokenAuthMiddleware(BaseHTTPMiddleware):
    """API Token 鉴权中间件

    检查规则：
    1. 公开路径 → 放行
    2. Authorization: Bearer <token> → 校验
    3. URL 参数 ?token=<token> → 校验（SSE 兼容）
    4. 无 token → 返回 401
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # 公开路径免鉴权
        if _is_public_path(path):
            return await call_next(request)

        # 获取当前有效 token
        valid_token = settings.JUNE_API_TOKEN or settings.JUNE_API_TOKEN

        # 方式一：Authorization Header
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            if token and valid_token and token == valid_token:
                return await call_next(request)
            # 开发模式无 token 配置时放行
            if not valid_token and not settings.is_production:
                return await call_next(request)

        # 方式二：URL 参数（SSE 兼容）
        query_token = request.query_params.get("token", "")
        if query_token:
            if valid_token and query_token == valid_token:
                return await call_next(request)
            if not valid_token and not settings.is_production:
                return await call_next(request)

        # 鉴权失败
        return JSONResponse(
            status_code=401,
            content={
                "code": 401,
                "message": "未授权访问，请提供有效的 API Token",
                "data": None,
                "timestamp": int(__import__("time").time() * 1000),
            },
        )
