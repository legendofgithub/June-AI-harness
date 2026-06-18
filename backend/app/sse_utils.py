"""
SSE 工具 — 流式响应心跳和超时保护

用法：
    from .sse_utils import sse_stream_with_heartbeat
    return EventSourceResponse(sse_stream_with_heartbeat(...))
"""
import asyncio
import json
import time
from typing import AsyncGenerator


async def sse_stream_with_heartbeat(
    chunk_generator: AsyncGenerator[str, None],
    thread_id: str,
    heartbeat_interval: int = 15,
    thread_timeout: int = 600,
) -> AsyncGenerator[dict, None]:
    """
    包装一个 chunk generator，为其添加：
    - 15 秒间隔的 SSE 心跳（": heartbeat" 注释行）
    - 10 分钟无活动自动超时关闭
    - CancelledError（客户端断开）优雅处理

    参数
    ----
    chunk_generator : 产生文本 delta 的异步生成器（来自 DeepSeekService.chat）
    thread_id : 当前线程 ID，用在 done 和 timeout 事件中
    heartbeat_interval : 心跳间隔（秒）
    thread_timeout : 无活动超时（秒）
    """
    last_activity = time.time()
    heartbeat_task: asyncio.Task | None = None
    timeout_task: asyncio.Task | None = None

    async def _heartbeat_loop(queue: asyncio.Queue):
        """定期向队列推送心跳事件"""
        try:
            while True:
                await asyncio.sleep(heartbeat_interval)
                await queue.put(None)  # None 表示心跳
        except asyncio.CancelledError:
            pass

    async def _timeout_loop(queue: asyncio.Queue):
        """检查是否超时"""
        try:
            while True:
                await asyncio.sleep(30)
                if time.time() - last_activity > thread_timeout:
                    await queue.put("timeout")
                    return
        except asyncio.CancelledError:
            pass

    heartbeat_queue: asyncio.Queue = asyncio.Queue()

    # 启动后台心跳和超时检查
    heartbeat_task = asyncio.create_task(_heartbeat_loop(heartbeat_queue))
    timeout_task = asyncio.create_task(_timeout_loop(heartbeat_queue))

    try:
        # 主循环：交替处理 chunk 和心跳
        chunk_iter = chunk_generator.__aiter__()

        while True:
            # 同时等待 chunk 或心跳/超时事件
            chunk_task = asyncio.create_task(chunk_iter.__anext__())

            done, _ = await asyncio.wait(
                [chunk_task, heartbeat_task, timeout_task,
                 asyncio.create_task(heartbeat_queue.get())],
                return_when=asyncio.FIRST_COMPLETED,
            )

            # 检查是否有超时信号
            if not heartbeat_queue.empty():
                signal = heartbeat_queue.get_nowait()
                if signal == "timeout":
                    yield {
                        "event": "timeout",
                        "data": json.dumps({
                            "message": "线程超时，已自动关闭",
                            "thread_id": thread_id,
                        }),
                    }
                    return

            # 检查心跳任务是否完成（异常退出）
            if heartbeat_task in done:
                # heartbeat 退出——重建之
                heartbeat_task.cancel()
                heartbeat_task = asyncio.create_task(_heartbeat_loop(heartbeat_queue))

            # 检查是否收到心跳信号
            hb_done = [t for t in done if t != chunk_task and t != heartbeat_task and t != timeout_task]
            if hb_done:
                # 发送心跳
                yield {
                    "event": "message",
                    "data": ": heartbeat",
                }
                last_activity = time.time()  # 心跳不算真正活动，但防止 timeout 误杀
                continue

            # 主 chunk 流
            if chunk_task in done:
                try:
                    delta = chunk_task.result()
                    last_activity = time.time()
                    yield {
                        "event": "message",
                        "data": json.dumps({"delta": delta, "type": "text"}),
                    }
                except StopAsyncIteration:
                    # chunk 流正常结束
                    yield {
                        "event": "done",
                        "data": json.dumps({"thread_id": thread_id, "usage": {}}),
                    }
                    return
                except Exception as exc:
                    yield {
                        "event": "error",
                        "data": json.dumps({"error": str(exc), "thread_id": thread_id}),
                    }
                    return

    except asyncio.CancelledError:
        # 客户端断开连接
        yield {
            "event": "done",
            "data": json.dumps({"reason": "client_disconnected", "thread_id": thread_id}),
        }
    except Exception as exc:
        yield {
            "event": "error",
            "data": json.dumps({"error": str(exc), "thread_id": thread_id}),
        }
    finally:
        # 清理后台任务
        if heartbeat_task and not heartbeat_task.done():
            heartbeat_task.cancel()
        if timeout_task and not timeout_task.done():
            timeout_task.cancel()
        # 避免 cancel 警告
        try:
            await asyncio.gather(heartbeat_task, timeout_task, return_exceptions=True)
        except Exception:
            pass
