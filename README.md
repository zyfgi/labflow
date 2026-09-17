# LabFlow — 高校科研实验室管理系统 V1

面向高校课题组/实验室（5–50 人）的管理系统，覆盖 **成员 → 学习进度/周报 → 科研项目/任务 → 实验记录 → 设备 → PI 看板** 的完整闭环。

## 技术栈

| 层 | 技术 |
| --- | --- |
| 前端 | Vue 3 + TypeScript + Vite + Element Plus + Pinia + Vue Router + Axios + ECharts + Day.js |
| 后端 | Python 3.12 + FastAPI + Pydantic v2 + SQLAlchemy 2 + Alembic + JWT (PyJWT) + pwdlib (argon2) |
| 数据库 | PostgreSQL 16（本地开发可用 SQLite，通过 `DATABASE_URL` 切换） |
| 部署 | Docker Compose（frontend / backend / postgres / nginx） |

## 快速开始（Docker Compose，推荐）

```bash
git clone <repo>
cd labflow
cp .env.example .env        # 修改所有密码与 SECRET_KEY
docker compose up -d --build
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.seed
```

访问 `http://localhost`，API 文档在 `http://localhost/api/docs`。

## 本地开发（不用 Docker）

```bash
# 后端
cd backend
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt     # Windows
# Linux/Mac: .venv/bin/pip install -r requirements.txt
# 配置 DATABASE_URL（默认 sqlite:///./labflow.db 可直接跑）
../.venv/Scripts/python -m alembic upgrade head   # 在 backend 目录下: .venv/Scripts/python -m alembic upgrade head
.venv/Scripts/python -m app.seed
.venv/Scripts/uvicorn app.main:app --reload --port 8000

# 前端
cd frontend
npm install
npm run dev        # http://localhost:5173，已配置 /api 代理到 8000
```

## Demo 账号（seed 生成，仅用于开发环境）

| 用户名 | 角色 | 说明 |
| --- | --- | --- |
| `admin` | PI | 实验室负责人，默认进入 Dashboard |
| `teacher01` | TEACHER | 教师 |
| `student01` … `student09` | STUDENT | 博士/硕士/本科生 |
| `equipadmin` | EQUIPMENT_ADMIN | 设备管理员 |

Seed 初始密码见 `.env.example` 注释 / `backend/app/seed.py` 顶部说明（开发环境使用，首次登录系统会提示修改密码）。

## 备份与恢复

```bash
./scripts/backup.sh              # 导出 PostgreSQL dump + storage/ 压缩包到 ./backups
./scripts/restore.sh <dump.sql> [storage.tar.gz]
```

详见 `docs/backup_restore.md`。

## 文档

- `docs/architecture.md` — 架构说明
- `docs/database.md` — 数据库 ER 说明
- `docs/api.md` — API 概览
- `docs/deployment.md` — 部署说明
- `docs/backup_restore.md` — 备份恢复
- `docs/ai-assistant.md` — AI 助手：配置、权限、安全边界
- `docs/retrieval-architecture.md` — 检索引擎（Search 与 AI 共用）
- `docs/security.md` — 安全设计
- `AGENT_PROGRESS.md` — 开发进度记录
- `FINAL_REPORT.md` — 最终交付报告

## AI 助手（可选）

只读实验室助手：问题 → 本地权限检索 → OpenAI-compatible 模型 → 回答 + 来源链接。
LLM 只能看见当前用户有权限的数据；API Key 仅保存在后端。

```env
# .env
AI_ENABLED=true
AI_BASE_URL=https://api.deepseek.com/v1   # 或 OpenAI / GLM / Qwen 等任意兼容端点
AI_API_KEY=sk-...
AI_MODEL=deepseek-chat
```

配置后重启 backend，左侧导航出现「AI 助手」。全部说明见 `docs/ai-assistant.md`。

## 生产安全

- 生产启动自动校验配置（DEBUG/SECRET_KEY/DATABASE_URL/AI 配置），不合格直接拒绝启动。
- 生产环境默认拒绝 demo seed；初始化管理员请使用：`docker compose exec backend python -m app.cli create-admin`。
