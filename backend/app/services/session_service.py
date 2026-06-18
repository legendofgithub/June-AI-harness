"""
会话服务 —— 会话生命周期管理、对话编排、追问链构建

纯业务逻辑，不接触 HTTP 请求/响应对象。
"""
from ..core.config import settings
from ..models.schemas import FollowUpRequest


class SessionService:
    """会话业务逻辑"""

    def __init__(self, session_repo, deepseek_service, thread_manager):
        self.repo = session_repo
        self.deepseek = deepseek_service
        self.thread_mgr = thread_manager

    # ---- 会话 CRUD ----

    def create_session(self, title: str = "新对话") -> dict:
        """创建新会话"""
        session = self.repo.create(title=title)
        return self._session_to_dict(session)

    def get_session(self, session_id: str) -> dict:
        """获取会话详情"""
        session = self.repo.get(session_id)
        messages = self.repo.get_messages(session_id)
        return {
            "id": session.id,
            "title": session.title,
            "created_at": int(session.created_at * 1000),
            "messages": messages,
        }

    def list_sessions(self, limit: int = 50) -> list[dict]:
        """获取会话列表"""
        sessions = self.repo.list_all(limit)
        return [self._session_to_dict(s) for s in sessions]

    def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        return self.repo.delete(session_id)

    def _session_to_dict(self, session) -> dict:
        return {
            "id": session.id,
            "title": session.title,
            "createdAt": int(session.created_at * 1000),
            "model": session.model,
        }

    # ---- 主对话 ----

    def ensure_session(self, session_id: str) -> dict:
        """确保会话存在（不存在则自动创建）"""
        session = self.repo.find(session_id)
        if session is None:
            session = self.repo.create()
        return {
            "id": session.id,
            "title": session.title,
            "created_at": int(session.created_at * 1000),
            "messages": self.repo.get_messages(session.id),
        }

    def save_user_message(self, session_id: str, content: str) -> dict:
        """保存用户消息"""
        msg = self.repo.add_message(session_id, "user", content, thread_id="main")
        return {
            "id": msg.id,
            "role": "user",
            "content": content,
            "timestamp": int(msg.timestamp * 1000),
            "threadId": "main",
        }

    async def stream_main_chat(
        self,
        session_id: str,
        session_messages: list[dict],
    ):
        """主对话 SSE 流式生成器"""
        full_content = ""
        main_thread_id = f"main_{session_id}"

        try:
            from ..thread_manager import ThreadInfo

            self.thread_mgr.register(ThreadInfo(
                thread_id=main_thread_id,
                parent_thread_id="root",
                session_id=session_id,
            ))
            self.thread_mgr.touch(main_thread_id)

            async for delta in self.deepseek.chat(
                messages=session_messages,
                api_key=self.deepseek.get_api_key(),
            ):
                full_content += delta
                yield {"delta": delta, "type": "text"}
        finally:
            if full_content:
                self.repo.add_message(session_id, "assistant", full_content, thread_id="main")

            yield {"done": True, "thread_id": main_thread_id, "usage": {}}
            self.thread_mgr.close(main_thread_id, cascade=False)

    # ---- 追问 ----

    async def stream_follow_up(
        self,
        session_id: str,
        body: FollowUpRequest,
    ):
        """追问 SSE 流式生成器"""
        from ..thread_manager import ThreadInfo

        self.thread_mgr.register(ThreadInfo(
            thread_id=body.thread_id,
            parent_thread_id=body.parent_thread_id,
            session_id=session_id,
        ))
        self.thread_mgr.touch(body.parent_thread_id)

        full_content = ""
        messages = self._build_follow_up_messages(body)

        try:
            self.thread_mgr.touch(body.thread_id)
            async for delta in self.deepseek.chat(
                messages=messages,
                api_key=self.deepseek.get_api_key(),
            ):
                full_content += delta
                yield {"delta": delta, "type": "text"}
        finally:
            yield {"done": True, "thread_id": body.thread_id, "usage": {}}
            self.thread_mgr.close(body.thread_id, cascade=False)

    def _build_follow_up_messages(self, body: FollowUpRequest) -> list[dict]:
        """构建追问的上下文 Prompt"""
        selected_text = body.source.selected_text or "截图内容"

        parent_context = ""
        if body.context.parent_thread_messages:
            parent_msgs = body.context.parent_thread_messages[-10:]
            parent_lines = []
            for m in parent_msgs:
                role_label = "学习者" if m.get("role") == "user" else "AI助手"
                parent_lines.append(f"[{role_label}]: {m.get('content', '')}")
            if parent_lines:
                parent_context = "### 父层对话历史\n" + "\n".join(parent_lines) + "\n"

        main_context = ""
        if body.context.main_thread_messages:
            main_msgs = body.context.main_thread_messages[-6:]
            main_lines = []
            for m in main_msgs:
                role_label = "学习者" if m.get("role") == "user" else "AI助手"
                main_lines.append(f"[{role_label}]: {m.get('content', '')}")
            if main_lines:
                main_context = "### 主对话历史\n" + "\n".join(main_lines) + "\n"

        context_prompt = f"""## 学习上下文
你正在帮助一位学习者理解以下内容。

### 当前追问链
- 这是第 L{body.level} 层追问

{parent_context}{main_context}
### 被选中的内容
>>> 被选中文本:
"{selected_text}"

### 追问
{body.query}

请针对被选中的内容进行详细解释。你的回答应该：
1. 先解释被选中文本的含义
2. 结合上下文补充相关背景
3. 如果涉及专业术语，提供通俗类比"""

        return [
            {
                "role": "system",
                "content": "你是 June AI，一位 AI 伴学助手。你善于用通俗易懂的语言解释复杂概念，并擅长引用上下文帮助学习者理解。",
            },
            {"role": "user", "content": context_prompt},
        ]
