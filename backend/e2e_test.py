"""E2E verification script for June AI backend — 10 critical-path tests"""
import os, sys, time, json, urllib.request, urllib.error, threading

os.environ['JUNE_ENV'] = 'development'
os.environ['JUNE_API_TOKEN'] = 'test-e2e-token-abc123'
os.environ['JUNE_DB_PATH'] = '/tmp/test-june-e2e.db'
os.environ['DEEPSEEK_API_KEY'] = ''

TOKEN = os.environ['JUNE_API_TOKEN']
BASE = 'http://127.0.0.1:8000'
passed = 0
failed = 0

def _api_get(path):
    """GET with token via query param"""
    r = urllib.request.urlopen(f'{BASE}/api{path}?token={TOKEN}', timeout=5)
    return json.loads(r.read())

def _api_delete(path):
    """DELETE with token via query param"""
    req = urllib.request.Request(f'{BASE}/api{path}?token={TOKEN}', method='DELETE')
    r = urllib.request.urlopen(req, timeout=5)
    return json.loads(r.read())

def _expect_401_http(fn):
    """Token middleware returns real HTTP 401 status"""
    try:
        fn()
        raise AssertionError('expected 401, got 200')
    except urllib.error.HTTPError as e:
        d = json.loads(e.read())
        assert e.code == 401, f'expected 401, got {e.code}'
        return d['message']

def check(name, fn):
    global passed, failed
    try:
        fn()
        print(f'  PASS: {name}')
        passed += 1
    except Exception as e:
        print(f'  FAIL: {name} -- {e}')
        failed += 1

# ── start backend in background thread ─────────────────────
print('Starting backend...')
import uvicorn
from app.main import app

t = threading.Thread(
    target=lambda: uvicorn.run(app, host='127.0.0.1', port=8000, log_level='error'),
    daemon=True,
)
t.start()

for i in range(15):
    time.sleep(2)
    try:
        if urllib.request.urlopen(f'{BASE}/health', timeout=3).status == 200:
            print(f'Backend ready after {(i + 1) * 2}s\n')
            break
    except Exception:
        pass
else:
    print('Backend failed to start!')
    sys.exit(1)

# ── 10 E2E tests ──────────────────────────────────────────

# 1. Health check (no auth)
check('GET /health returns 200', lambda: print(
    '   ', json.loads(urllib.request.urlopen(BASE + '/health', timeout=5).read())
))

# 2. No token → HTTP 401
check('GET /api/status without token → HTTP 401',
      lambda: print('   ', _expect_401_http(
          lambda: urllib.request.urlopen(BASE + '/api/status', timeout=5)
      )))

# 3. Wrong token → HTTP 401
check('GET /api/status with wrong token → HTTP 401',
      lambda: print('   ', _expect_401_http(
          lambda: urllib.request.urlopen(
              urllib.request.Request(BASE + '/api/status',
                                     headers={'Authorization': 'Bearer wrong-token'}),
              timeout=5,
          )
      )))

# 4. Correct token → /api/status (returns flat dict, no Result wrapper)
def t4():
    d = _api_get('/status')
    print(f'   version={d["version"]}, env={d["env"]}, db={d["db"]}')
    assert d['db'] == 'connected'

check('GET /api/status with correct token → 200', t4)

# 5. Session list
def t5():
    d = _api_get('/sessions')
    print(f'   code={d["code"]}, sessions={len(d["data"])}')
    assert d['code'] == 200

check('GET /api/sessions → 200', t5)

# 6. Create session
sid_box = [None]

def t6():
    data = json.dumps({'title': 'E2E Test Session'}).encode()
    req = urllib.request.Request(
        BASE + '/api/sessions?token=' + TOKEN,
        data=data,
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    r = urllib.request.urlopen(req, timeout=5)
    d = json.loads(r.read())
    assert d['code'] == 200
    assert d['data']['title'] == 'E2E Test Session'
    sid_box[0] = d['data']['id']
    print(f'   id={sid_box[0]}, title={d["data"]["title"]}')

check('POST /api/sessions create session', t6)
sid = sid_box[0]

# 7. Get single session
def t7():
    d = _api_get('/sessions/' + sid)
    print(f'   code={d["code"]}, messages={len(d["data"].get("messages", []))}')
    assert d['code'] == 200

check('GET /api/sessions/<id> → 200', t7)

# 8. Nonexistent → HTTP 200 + JSON code:404
def t8():
    d = _api_get('/sessions/nonexistent')
    print(f'   code={d["code"]}, msg={d["message"]}')
    assert d['code'] == 404

check('GET /api/sessions/nonexistent → JSON code:404', t8)

# 9. Delete session
def t9():
    d = _api_delete('/sessions/' + sid)
    print(f'   code={d["code"]}, msg={d["message"]}')
    assert d['code'] == 200

check('DELETE /api/sessions/<id> → 200', t9)

# 10. 404 after delete
def t10():
    d = _api_get('/sessions/' + sid)
    print(f'   code={d["code"]}, msg={d["message"]}')
    assert d['code'] == 404

check('GET /api/sessions/<id> after delete → JSON code:404', t10)

# ── report ────────────────────────────────────────────────
print(f'\n========== Results: {passed} passed, {failed} failed ==========')
sys.exit(1 if failed else 0)
