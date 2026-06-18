@echo off
chcp 65001 >nul
title June AI 伴学系统 - 启动器

echo ========================================
echo   June AI 伴学系统 v2.0 启动中...
echo ========================================
echo.

:: 检查 .env 文件，不存在则从模板复制
if not exist "backend\.env" (
    if exist "backend\.env.example" (
        echo [0] 未检测到 .env 文件，正从 .env.example 复制...
        copy "backend\.env.example" "backend\.env" >nul
        echo     已创建 .env 文件，请根据需要修改配置
        echo     重要：生产部署前请修改 JUNE_API_TOKEN 和 DEEPSEEK_API_KEY
    ) else (
        echo [警告] .env.example 不存在，将使用默认配置
    )
)

:: 检查 Python 依赖
echo [检查] Python 依赖...
".venv\Scripts\python.exe" -c "import uvicorn, fastapi" 2>nul
if %errorlevel% neq 0 (
    echo   [安装] 正在安装后端依赖...
    ".venv\Scripts\pip.exe" install -r backend\requirements.txt --quiet
)

:: 启动守护进程（含后端自动重启）
echo [1/2] 启动后端守护（端口 8000）—— 崩溃自动重启
start "JuneAI-Watchdog" cmd /c "cd /d "D:\AI\claude-code-project\ai-study-tool" && ".venv\Scripts\python.exe" watchdog.py --port 8000"

echo   等待后端就绪（最多 30 秒）...
set /a count=0
:wait_loop
timeout /t 2 /nobreak >nul
curl -s http://localhost:8000/health >nul 2>&1
if %errorlevel% equ 0 goto backend_ok
set /a count+=2
if %count% lss 30 goto wait_loop

echo   后端启动超时，请检查 ./backend 目录
goto skip_backend

:backend_ok
echo   后端: http://localhost:8000 [OK]

:skip_backend
echo.
echo [2/2] 启动前端 (端口 5173)...
start "JuneAI-Frontend" cmd /c "cd /d "D:\AI\claude-code-project\ai-study-tool\frontend" && npx vite --host 0.0.0.0 --port 5173"

echo   等待前端启动...
timeout /t 5 /nobreak >nul
curl -s http://localhost:5173 >nul 2>&1
if %errorlevel% equ 0 (
    echo   前端: http://localhost:5173 [OK]
) else (
    echo   前端可能仍在启动中，请查看新窗口的输出
)

echo.
echo ========================================
echo   June AI 伴学系统 v2.0
echo   前端: http://localhost:5173
echo   后端: http://localhost:8000（守护中，崩溃自动重启）
echo.
echo   首次使用请在后端窗口复制 API Token
echo   粘贴到前端设置页面即可连接
echo ========================================
echo.
pause
