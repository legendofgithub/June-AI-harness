"""
SQLAlchemy ORM 模型定义

三张核心表：
- sessions:   会话（对话记录）
- messages:   消息（用户/AI 对话内容）
- threads:    追问线程（树状追问链，parent_thread_id 自引用）
"""
import uuid
import time
from sqlalchemy import Column, String, Integer, Text, Float, Boolean, ForeignKey, create_engine
from sqlalchemy.orm import declarative_base, relationship, Session

Base = declarative_base()


def gen_id() -> str:
    return str(uuid.uuid4())


def now_ms() -> int:
    return int(time.time() * 1000)


class SessionModel(Base):
    """会话表"""
    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, default=gen_id)
    title = Column(String(200), nullable=False, default="新对话")
    model = Column(String(50), nullable=False, default="deepseek-chat")
    created_at = Column(Float, default=lambda: time.time())
    updated_at = Column(Float, default=lambda: time.time(), onupdate=lambda: time.time())

    # 关联
    messages = relationship("MessageModel", back_populates="session", cascade="all, delete-orphan",
                            order_by="MessageModel.timestamp")
    threads = relationship("ThreadModel", back_populates="session", cascade="all, delete-orphan")


class MessageModel(Base):
    """消息表（用户消息 + AI 回复）"""
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=gen_id)
    session_id = Column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # user / assistant
    content = Column(Text, nullable=False, default="")
    thread_id = Column(String(100), nullable=False, default="main")  # 所属线程标识
    timestamp = Column(Float, default=lambda: time.time())

    # 反向关联
    session = relationship("SessionModel", back_populates="messages")


class ThreadModel(Base):
    """追问线程表（树状结构，parent_thread_id 指向父线程）"""
    __tablename__ = "threads"

    id = Column(String(100), primary_key=True)  # thread_id，如 "main_<session_id>" 或 UUID
    session_id = Column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_thread_id = Column(String(100), nullable=True, index=True)  # 父线程 ID，"root" 表示根
    level = Column(Integer, nullable=False, default=1)  # 追问层级：1=主对话, 2=L2追问...
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(Float, default=lambda: time.time())
    last_activity = Column(Float, default=lambda: time.time())

    # 反向关联
    session = relationship("SessionModel", back_populates="threads")


# ---- 数据库引擎（按需创建） ----

_engine = None


def get_engine(db_path: str):
    """获取数据库引擎（单例）"""
    global _engine
    if _engine is None:
        _engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},  # SQLite 多线程支持
            echo=False,
        )
    return _engine


def init_db(db_path: str) -> None:
    """初始化数据库：创建所有表"""
    engine = get_engine(db_path)
    Base.metadata.create_all(engine)


def get_session(db_path: str) -> Session:
    """获取新的数据库会话"""
    return Session(get_engine(db_path))
