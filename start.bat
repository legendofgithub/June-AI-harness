@echo off
chcp 65001 >nul
title June AI 伴学系统 - 启动器

echo ========================================
echo   June AI 伴学系统 v2.0
echo ========================================
echo.

cd /d "%~dp0"

:: ── 0. 检查 .env ──────────────────────────────
if not exist "backend\.env" (
    if exist "backend\.env.example" (
        echo [0] 未检测到 backend\.env，正从 .env.example 复制...
        copy "backend\.env.example" "backend\.env" >nul
        echo     已创建，请按需修改 DEEPSEEK_API_KEY 和 JUNE_API_TOKEN
    ) else (
        echo [警告] backend\.env.example 不存在
    )
)

:: ── 1. 检查虚拟环境 ──────────────────────────
set "VENV_PYTHON=.venv\Scripts\python.exe"
set "VENV_PIP=.venv\Scripts\pip.exe"

if not exist "%VENV_PYTHON%" (
    echo [1] 正在创建虚拟环境...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo [错误] 创建虚拟环境失败，请确认 Python 已安装且在 PATH 中
        pause
        exit /b 1
    )
    echo     虚拟环境已创建
)

:: ── 2. 安装依赖 ──────────────────────────────
echo [2] 检查 Python 依赖...
"%VENV_PYTHON%" -c "import uvicorn, fastapi, sqlalchemy" 2>nul
if %errorlevel% neq 0 (
    echo     正在安装（首次较慢，请耐心等待）...
    "%VENV_PIP%" install -r backend\requirements.txt -q
    if %errorlevel% neq 0 (
        echo [错误] 依赖安装失败
        pause
        exit /b 1
    )
)

:: ── 3. 安装前端依赖 ──────────────────────────
echo [3] 检查前端依赖...
if not exist "frontend\node_modules" (
    echo     首次启动，正在安装前端依赖...
    cd frontend
    call npm install --legacy-peer-deps
    if %errorlevel% neq 0 (
        echo [错误] 前端依赖安装失败，请确认 Node.js 已安装
        cd ..
        pause
        exit /b 1
    )
    cd ..
)

:: ── 4. 启动后端守护 ──────────────────────────
echo.
echo [4] 启动后端守护（端口 8000，崩溃自动重启）...
start "JuneAI-Backend" cmd /c "cd /d "%~dp0" && "%VENV_PYTHON%" watchdog.py --port 8000"

echo     等待就绪（最多 30 秒）...
for /l %%i in (1,1,15) do (
    timeout /t 2 /nobreak >nul
    "%VENV_PYTHON%" -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)" 2>nul && goto backend_ok
)
echo     后端启动超时，请查看新窗口的输出
goto skip_backend

:backend_ok
echo     后端: http://localhost:8000 ^(PID 见守护窗口^)

:skip_backend

:: ── 5. 启动前端 ──────────────────────────────
echo.
echo [5] 启动前端（端口 5173）...
start "JuneAI-Frontend" cmd /c "cd /d "%~dp0frontend" && npx vite --host 0.0.0.0 --port 5173"

echo     等待启动...
timeout /t 4 /nobreak >nul

echo.
echo ========================================
echo   June AI v2.0 启动完成
echo   前端: http://localhost:5173
echo   后端: http://localhost:8000
echo.
echo   首次使用：
echo   1. 打开前端页面
echo   2. 查看后端窗口的 API Token
echo   3. 在前端设置中粘贴验证
echo ========================================
echo.
pause
