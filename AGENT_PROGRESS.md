# LabFlow 开发进度（AGENT_PROGRESS）

> 无人值守一次性执行模式。每个 Milestone 记录：已完成内容 / 修改文件 / 数据库变化 / API / 测试证据 / 已知问题 / 下一步。

---

# Milestone 0 — 初始化

## Completed

- Git 仓库初始化（main 分支），目录结构：`frontend/ backend/ storage/ scripts/ docs/ nginx/`
- 后端 FastAPI 骨架：`app/main.py`（app 工厂、CORS 可配置）、`app/core/config.py`（pydantic-settings）、`app/database.py`（SQLAlchemy 2 engine/session）
- `GET /api/health` 健康检查
- 前端 Vue3 + Vite + TS + Element Plus + Pinia + Router 骨架，首页读取后端健康状态
- Docker Compose 四容器编排：postgres(16-alpine) / backend / frontend / nginx（边界反代 80 → 前端静态 + /api → 后端）
- nginx 配置（边界 + 前端静态 SPA fallback）
- `.env.example`（所有密钥为占位符）、`.gitignore`（排除 .env / node_modules / storage 上传件 / pgdata 等）
- `scripts/backup.sh`、`scripts/restore.sh`（PostgreSQL dump + storage 归档）
- 本地验证环境：本机无 Docker/PostgreSQL，采用嵌入式 PostgreSQL 16.2（pgserver 二进制复制到纯 ASCII 路径 `C:\Users\14993\.labflow_pginstall`，数据目录 `C:\Users\14993\.labflow_pgdata`），`scripts/dev_pg.py` 辅助

## Files Changed

- 新增：`.gitignore` `.env.example` `docker-compose.yml` `nginx/default.conf` `nginx/frontend.conf` `README.md`
- 新增：`backend/Dockerfile` `backend/app/**`（骨架）`backend/.env`（本地，不入库）
- 新增：`frontend/package.json` `frontend/vite.config.ts` `frontend/tsconfig.json` `frontend/index.html` `frontend/Dockerfile` `frontend/nginx.conf` `frontend/src/**`（骨架）
- 新增：`scripts/backup.sh` `scripts/restore.sh` `scripts/dev_pg.py` `storage/.gitkeep`

## Database Changes

- 创建数据库 `labflow`（PostgreSQL 16.2，UTF8）。尚无业务表（Milestone 1 引入 Alembic）。

## API Added

- `GET /api/health` → 200 `{"status":"ok","app":"LabFlow","env":"development"}`

## Tests

Command:

```bash
cd backend && .venv/Scripts/python -m uvicorn app.main:app --port 8000   # 后台
curl -s http://127.0.0.1:8000/api/health
cd frontend && npm run build
```

Result:

```text
{"status":"ok","app":"LabFlow","env":"development"}  (HTTP 200)
vite build: ✓ built in 9.17s
```

## Manual Verification

- 健康检查 200 ✅（真实 HTTP 请求）
- 前端生产构建成功 ✅
- Docker：本机无 Docker，`docker compose up` 无法本机执行；compose/nginx/Dockerfile 已按规范交付，M9 复核语法与配置一致性（已知限制，见 FINAL_REPORT）

## Known Issues

- 本机 Windows 无 Docker：Docker Compose 无法本机启动验证（文件已交付）
- pgserver initdb 在含中文的路径/GBK locale 下失败：已用 `--locale=C` + 纯 ASCII 路径绕过；崩溃恢复期间日志文件有 30s 共享冲突重试窗口，自动恢复

## Next Step

Milestone 1：User/MemberProfile 模型、Alembic、JWT 认证、RBAC、用户管理、登录页、基础 Layout
