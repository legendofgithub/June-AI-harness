"""
June AI 进程守护 —— health 探测 + 自动重启

每 10 秒向 http://127.0.0.1:{port}/health 发 GET 请求，
连续 3 次失败则 kill 旧进程并重启 uvicorn。

用法：
  python watchdog.py                    # 默认 8000 端口
  python watchdog.py --port 8001        # 指定端口
"""
import argparse
import os
import signal
import subprocess
import sys
import time
import urllib.request
from datetime import datetime


class Watchdog:
    def __init__(self, port: int = 8000, check_interval: int = 10, max_failures: int = 3):
        self.port = port
        self.check_interval = check_interval
        self.max_failures = max_failures
        self.process: subprocess.Popen | None = None
        self.failure_count = 0
        self.restart_count = 0

    def _log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] {msg}")

    def _check_health(self) -> bool:
        """向 /health 端点发 GET，返回 True 表示健康"""
        try:
            url = f"http://127.0.0.1:{self.port}/health"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return False

    def _start_backend(self):
        """启动 uvicorn 子进程"""
        backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
        cmd = [
            sys.executable, "-m", "uvicorn", "app.main:app",
            "--host", "0.0.0.0",
            "--port", str(self.port),
        ]
        self._log(f"启动后端进程（端口 {self.port}）")
        # Windows 用 CREATE_NEW_PROCESS_GROUP，Linux 用 start_new_session
        kwargs = {}
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            kwargs["start_new_session"] = True

        self.process = subprocess.Popen(
            cmd,
            cwd=backend_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            **kwargs,
        )
        self.restart_count += 1

    def _kill_backend(self):
        """安全终止旧进程"""
        if self.process is None:
            return
        try:
            if sys.platform == "win32":
                # Windows: 发 Ctrl+C 信号
                self.process.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                self.process.send_signal(signal.SIGTERM)
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=3)
        except Exception:
            try:
                self.process.kill()
            except Exception:
                pass
        self._log(f"已终止旧进程（共重启 {self.restart_count} 次）")

    def run(self):
        """主循环：启动 → 持续探测 → 失败重启"""
        self._start_backend()

        # 给首次启动留 10 秒缓冲
        self._log(f"等待后端就绪（最多 30 秒）...")
        for _ in range(6):
            time.sleep(5)
            if self._check_health():
                self._log("后端就绪 ✓")
                break

        while True:
            try:
                time.sleep(self.check_interval)

                if self._check_health():
                    # 探测成功 → 重置失败计数器
                    if self.failure_count > 0:
                        self._log(f"探测恢复（连续 {self.failure_count} 次失败后恢复）")
                    self.failure_count = 0
                else:
                    self.failure_count += 1
                    self._log(f"探测失败 ({self.failure_count}/{self.max_failures})")

                    if self.failure_count >= self.max_failures:
                        self._log(f"连续 {self.max_failures} 次探测失败，重启后端...")
                        self._kill_backend()
                        time.sleep(2)
                        self._start_backend()
                        self.failure_count = 0

                        # 等新进程就绪
                        for _ in range(6):
                            time.sleep(5)
                            if self._check_health():
                                self._log("后端已恢复 ✓")
                                break

            except KeyboardInterrupt:
                self._log("收到退出信号")
                break
            except Exception as e:
                self._log(f"Watchdog 自身异常: {e}")

        self._kill_backend()
        self._log("Watchdog 已退出")


def main():
    parser = argparse.ArgumentParser(description="June AI 进程守护")
    parser.add_argument("--port", type=int, default=8000, help="后端端口（默认 8000）")
    parser.add_argument("--interval", type=int, default=10, help="探测间隔秒数（默认 10）")
    parser.add_argument("--max-failures", type=int, default=3, help="连续失败阈值（默认 3）")
    args = parser.parse_args()

    wd = Watchdog(port=args.port, check_interval=args.interval, max_failures=args.max_failures)
    print("=" * 50)
    print(f"  June AI 进程守护 v2.0")
    print(f"  端口: {args.port}")
    print(f"  探测间隔: {args.interval}s")
    print(f"  失败阈值: {args.max_failures} 次")
    print("=" * 50)
    wd.run()


if __name__ == "__main__":
    main()
