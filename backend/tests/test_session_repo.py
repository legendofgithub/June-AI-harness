"""
SessionRepository 单元测试 —— 使用 /tmp 目录直接建 SQLite
"""
import pytest
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.models.database import Base
from app.repositories.session_repo import SessionRepository
from app.core.exceptions import NotFoundException

@pytest.fixture
def repo():
    db_path = os.path.join('/tmp', f'june_test_{os.getpid()}.db')
    engine = create_engine(f'sqlite:///{db_path}', connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    db = Session(engine)
    r = SessionRepository(db)
    yield r
    db.close()
    engine.dispose()
    os.unlink(db_path)


class TestSessionRepository:
    def test_create_session(self, repo):
        s = repo.create(title="测试")
        assert s.id is not None
        assert s.title == "测试"
    def test_default_title(self, repo):
        assert repo.create().title == "新对话"
    def test_get_session(self, repo):
        c = repo.create(title="X"); f = repo.get(c.id); assert f.title == "X"
    def test_get_raises(self, repo):
        with pytest.raises(NotFoundException): repo.get("no")
    def test_find_none(self, repo):
        assert repo.find("no") is None
    def test_find_ok(self, repo):
        c = repo.create(); assert repo.find(c.id).id == c.id
    def test_exists_true(self, repo):
        assert repo.exists(repo.create().id)
    def test_exists_false(self, repo):
        assert not repo.exists("no")
    def test_list_all(self, repo):
        repo.create(); repo.create(); assert len(repo.list_all()) == 2
    def test_update_title(self, repo):
        c = repo.create(title="旧"); repo.update_title(c.id, "新")
        assert repo.get(c.id).title == "新"
    def test_delete(self, repo):
        c = repo.create(); repo.delete(c.id); assert not repo.exists(c.id)
    def test_delete_false(self, repo):
        assert not repo.delete("no")
    def test_add_message(self, repo):
        s = repo.create(); m = repo.add_message(s.id, "user", "hi")
        assert m.content == "hi"
    def test_get_messages(self, repo):
        s = repo.create()
        repo.add_message(s.id, "user", "a"); repo.add_message(s.id, "assistant", "b")
        msgs = repo.get_messages(s.id)
        assert len(msgs) == 2; assert msgs[0]["content"] == "a"
    def test_messages_by_thread(self, repo):
        s = repo.create()
        repo.add_message(s.id, "user", "main", thread_id="main")
        repo.add_message(s.id, "user", "f1", thread_id="followup_1")
        assert len(repo.get_messages(s.id, thread_id="main")) == 1
    def test_add_message_auto_create(self, repo):
        m = repo.add_message("auto-99", "user", "hi")
        assert repo.exists("auto-99")
