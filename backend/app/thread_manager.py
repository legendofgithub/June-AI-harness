"""
ThreadManager — 追问线程生命周期管理

负责：
- 注册/追踪所有追问线程
- 空闲超时自动清理（默认 10 分钟无活动）
- 级联关闭子线程
- 配合 FastAPI lifespan 启动/停止后台清理任务
"""
import asyncio
import time
from dataclasses import dataclass, field


@dataclass
class ThreadInfo:
    thread_id: str
    parent_thread_id: str
    session_id: str
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    is_active: bool = True


class ThreadManager:
    def __init__(self, idle_timeout: int = 600):
        """
        idle_timeout: 空闲超时秒数，默认 600（10 分钟）。
        超过此时间无活动的追问线程将被标记为可清理。
        """
        self._threads: dict[str, ThreadInfo] = {}
        self._idle_timeout = idle_timeout
        self._cleanup_task: asyncio.Task | None = None

    # ---- 注册 / 追踪 ----

    def register(self, info: ThreadInfo) -> None:
        """注册新的追问线程"""
        self._threads[info.thread_id] = info

    def touch(self, thread_id: str) -> None:
        """更新线程的最后活动时间（收到消息时调用）"""
        if thread_id in self._threads:
            self._threads[thread_id].last_activity = time.time()

    # ---- 关闭 ----

    def close(self, thread_id: str, cascade: bool = True) -> None:
        """关闭线程，cascade=True 时级联关闭所有子线程"""
        if cascade:
            children = [
                tid for tid, t in self._threads.items()
                if t.parent_thread_id == thread_id and t.is_active
            ]
            for child_id in children:
                self.close(child_id, cascade=True)

        if thread_id in self._threads:
            self._threads[thread_id].is_active = False

    # ---- 查询 ----

    def get_active_threads(self) -> list[ThreadInfo]:
        """获取所有活跃线程"""
        return [t for t in self._threads.values() if t.is_active]

    def get_thread(self, thread_id: str) -> ThreadInfo | None:
        """按 ID 获取线程"""
        return self._threads.get(thread_id)

    def active_count(self) -> int:
        """当前活跃线程数"""
        return sum(1 for t in self._threads.values() if t.is_active)

    # ---- 后台清理 ----

    async def start_cleanup(self, interval: int = 60) -> None:
        """
        启动后台清理任务，每 interval 秒扫描一次。
        在 FastAPI lifespan startup 中调用。
        """
        if self._cleanup_task is not None:
            return  # 已启动

        async def _cleanup_loop():
            while True:
                try:
                    await asyncio.sleep(interval)
                    now = time.time()
                    to_close: list[str] = []
                    for tid, t in self._threads.items():
                        if t.is_active and (now - t.last_activity > self._idle_timeout):
                            to_close.append(tid)

                    for tid in to_close:
                        self.close(tid, cascade=True)

                    if to_close:
                        print(f"[ThreadManager] 清理了 {len(to_close)} 个空闲线程: {to_close}")
                except asyncio.CancelledError:
                    break
                except Exception as exc:
                    print(f"[ThreadManager] 清理循环异常: {exc}")

        self._cleanup_task = asyncio.create_task(_cleanup_loop())

    async def stop_cleanup(self) -> None:
        """停止后台清理任务。在 FastAPI lifespan shutdown 中调用。"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None


# 全局单例，供整个应用使用
thread_manager = ThreadManager(idle_timeout=600)
