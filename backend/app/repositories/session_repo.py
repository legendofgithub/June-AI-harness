"""
会话仓库 —— 封装 sessions 和 messages 表的所有数据库操作。

命名约定（参照 AgentX）：
- get_xxx()   → 必须返回结果，否则抛 NotFoundException
- find_xxx()  → 可返回 None
- exists_xxx() → 返回 bool
"""
import time
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
from ..models.database import SessionModel, MessageModel
from ..core.exceptions import NotFoundException


class SessionRepository:
    """会话持久化操作"""

    def __init__(self, db: Session):
        self.db = db

    # ---- 创建 ----

    def create(self, title: str = "新对话", model: str = "deepseek-chat") -> SessionModel:
        """创建新会话"""
        session = SessionModel(title=title, model=model)
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    # ---- 查询 ----

    def get(self, session_id: str) -> SessionModel:
        """获取会话，不存在则抛 NotFoundException"""
        session = self.db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if session is None:
            raise NotFoundException(f"会话 {session_id} 不存在")
        return session

    def find(self, session_id: str) -> Optional[SessionModel]:
        """查找会话，不存在返回 None"""
        return self.db.query(SessionModel).filter(SessionModel.id == session_id).first()

    def list_all(self, limit: int = 50) -> list[SessionModel]:
        """获取所有会话列表（按更新时间降序）"""
        return (
            self.db.query(SessionModel)
            .order_by(desc(SessionModel.updated_at))
            .limit(limit)
            .all()
        )

    def exists(self, session_id: str) -> bool:
        """检查会话是否存在"""
        return self.db.query(SessionModel).filter(SessionModel.id == session_id).first() is not None

    # ---- 更新 ----

    def update_title(self, session_id: str, title: str) -> SessionModel:
        """更新会话标题"""
        session = self.get(session_id)
        session.title = title
        session.updated_at = time.time()
        self.db.commit()
        return session

    def touch(self, session_id: str) -> None:
        """更新会话最后活跃时间"""
        session = self.find(session_id)
        if session:
            session.updated_at = time.time()
            self.db.commit()

    # ---- 删除 ----

    def delete(self, session_id: str) -> bool:
        """删除会话（级联删除关联的 messages 和 threads）"""
        session = self.find(session_id)
        if session is None:
            return False
        self.db.delete(session)
        self.db.commit()
        return True

    # ---- 消息操作 ----

    def add_message(self, session_id: str, role: str, content: str, thread_id: str = "main") -> MessageModel:
        """添加消息到会话"""
        # 确保会话存在
        session = self.find(session_id)
        if session is None:
            session = self.create(title="新对话")
            session_id = session.id

        msg = MessageModel(
            session_id=session_id,
            role=role,
            content=content,
            thread_id=thread_id,
        )
        self.db.add(msg)
        self.touch(session_id)
        self.db.commit()
        return msg

    def get_messages(self, session_id: str, thread_id: Optional[str] = None, limit: int = 200) -> list[dict]:
        """获取会话消息列表（返回字典格式，兼容前端）"""
        query = self.db.query(MessageModel).filter(MessageModel.session_id == session_id)
        if thread_id:
            query = query.filter(MessageModel.thread_id == thread_id)
        msgs = query.order_by(MessageModel.timestamp).limit(limit).all()
        return [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "timestamp": int(m.timestamp * 1000),
                "threadId": m.thread_id,
            }
            for m in msgs
        ]
