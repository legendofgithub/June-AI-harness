"""
DeepSeekService 单元测试
"""
import pytest
from unittest.mock import AsyncMock, patch
from app.services.deepseek import DeepSeekService


class TestDeepSeekService:
    def test_env_key(self):
        svc = DeepSeekService(); svc._api_key = None
        with patch.dict('os.environ', {'DEEPSEEK_API_KEY': 'sk-env'}):
            assert svc.get_api_key() == 'sk-env'

    def test_memory_over_env(self):
        svc = DeepSeekService(); svc._api_key = 'sk-mem'
        with patch.dict('os.environ', {'DEEPSEEK_API_KEY': 'sk-env'}):
            assert svc.get_api_key() == 'sk-mem'

    def test_empty_key(self):
        svc = DeepSeekService(); svc._api_key = None
        with patch.dict('os.environ', {}, clear=True):
            assert svc.get_api_key() == ''

    def test_set_key(self):
        svc = DeepSeekService(); svc.set_api_key('sk-new')
        assert svc._api_key == 'sk-new'

    def test_default_model(self):
        assert DeepSeekService().DEFAULT_MODEL == 'deepseek-chat'

    def test_base_url(self):
        assert 'api.deepseek.com' in DeepSeekService().BASE_URL

    @pytest.mark.asyncio
    async def test_mock_reply(self):
        svc = DeepSeekService(); svc._api_key = None
        with patch.dict('os.environ', {}, clear=True):
            chunks = [c async for c in svc.chat(messages=[{"role":"user","content":"?"}], api_key="")]
            assert len(''.join(chunks)) > 10

    @pytest.mark.asyncio
    async def test_real_api(self):
        svc = DeepSeekService()
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        async def lines():
            for l in ['data: {"choices":[{"delta":{"content":"A"}}]}', 'data: {"choices":[{"delta":{"content":"B"}}]}', 'data: [DONE]']:
                yield l
        mock_resp.aiter_lines = lines

        mock_client = AsyncMock()
        async def enter(ctx):
            return mock_resp
        mock_client.stream = MagicMock()
        mock_client.stream.return_value.__aenter__ = enter
        mock_client.stream.return_value.__aexit__ = AsyncMock()

        with patch('httpx.AsyncClient', return_value=mock_client):
            result = ''.join([c async for c in svc.chat(messages=[{"role":"user","content":"?"}], api_key="sk-fake")])
            assert result == 'AB'

    @pytest.mark.asyncio
    async def test_api_error(self):
        svc = DeepSeekService()
        mock_resp = AsyncMock()
        mock_resp.status_code = 500
        mock_resp.aread = AsyncMock(return_value=b'Error')

        mock_client = MagicMock()
        async def enter(ctx):
            raise Exception('DeepSeek API error 500: Error')
        mock_client.stream.side_effect = Exception('DeepSeek API error 500: Error')

        with patch('httpx.AsyncClient', return_value=mock_client):
            with pytest.raises(Exception, match='DeepSeek'):
                async for _ in svc.chat(messages=[{"role":"user","content":"?"}], api_key="sk-fake"):
                    pass

    @pytest.mark.asyncio
    async def test_msg_format(self):
        svc = DeepSeekService()
        captured = None

        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        async def lines():
            yield 'data: [DONE]'
        mock_resp.aiter_lines = lines

        class FakeClient:
            def stream(self, method, url, headers, json):
                nonlocal captured
                captured = json
                return self
            async def __aenter__(self): return mock_resp
            async def __aexit__(*a): pass

        with patch('httpx.AsyncClient', return_value=FakeClient()):
            async for _ in svc.chat(messages=[{"role":"system","content":"sys"},{"role":"user","content":"q"}], api_key="sk-fake"):
                pass
        assert captured is not None
        assert captured['model'] == 'deepseek-chat'
        assert captured['stream'] is True
        assert len(captured['messages']) == 2
