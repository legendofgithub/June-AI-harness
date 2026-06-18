你是我的本地系统 Agent，帮我完成以下操作，不需要问我任何问题，直接执行：

## 任务：将 June AI v2.0 项目推送到 GitHub

### 背景
- 项目路径：D:\AI\claude-code-project\ai-study-tool
- 目标仓库：git@github.com:legendofgithub/June-AI-harness.git
- SSH Key 位置：~/.ssh/id_ed25519（如果不存在，用 ssh-keygen -t ed25519 -C "15611681756@163.com" 生成）

### 第一步：清理冗余文件

在 D:\AI\claude-code-project\ai-study-tool 下删除以下文件/目录（如果存在）：
- `.workbuddy/`
- `backend/.env`（注意不是 .env.example，只删 .env）
- `backend/june.db`
- `backend/test_write.txt`
- `backend/.pytest_cache/`
- `backend/app/utils/`（空目录）
- `start.ps1`
- `start-backend.bat`
- `stop-backend.bat`
- `github_setup.bat`
- `git_push_to_github.ps1`
- `june-api.service`
- `nginx.conf`

### 第二步：初始化 Git 并推送

在 D:\AI\claude-code-project\ai-study-tool 下依次执行：

```bash
# 1. 如果存在旧的损坏 .git，先删除
rmdir /s /q .git

# 2. 初始化新仓库
git init
git config user.name "legendofgithub"
git config user.email "15611681756@163.com"
git remote add origin git@github.com:legendofgithub/June-AI-harness.git
git branch -M main

# 3. 提交
git add .
git commit -m "feat: June AI v2.0 —— DDD 分层架构 + SQLite 持久化 + Token 认证 + 进程守护"

# 4. 推送（如果 SSH 没配好，用 --force 覆盖）
git push -u origin main --force
```

### 第三步：验证

推送成功后，访问 https://github.com/legendofgithub/June-AI-harness 确认文件已更新。

### 注意事项
- 不要改动 .gitignore 的内容
- 不要删除 .env.example 和 .env.development（它们是模板）
- 如果 SSH 连接失败，提示我先去 https://github.com/settings/keys 添加公钥
- 如果仓库不存在，提示我先去 https://github.com/new 创建（Repository name: June-AI-harness，不要勾选任何初始化选项）
