# LabFlow — 高校科研实验室管理系统 V1

面向高校课题组/实验室（5–50 人）的管理系统，覆盖 **成员 → 学习进度/周报 → 科研项目/任务 → 实验记录 → 设备 → PI 看板** 的完整闭环。

## 轻流程协同（产品原则）

**LabFlow 是科研协同记录系统，不是 OA 审批系统。**

系统采用轻流程协同：默认直接执行，相关人员自动收到通知，所有关键操作留痕。

- 周报：草稿 → **发布**（无需审核），发布后仍可继续修改并自动通知关注人；同事通过评论交流。
- 设备预约：无时间冲突即**立即生效**，冲突是唯一硬阻断（409）；没有审批环节。
- 设备借用：设备可用即借出；归还、**延期**（直接改应还时间）都不需要批准。
- 故障：上报**立即**把设备置为故障，不等管理员确认。
- 任务：分配/改派/改期/完成立即生效，旧与新负责人自动收到通知。
- 项目成员：添加立即生效，不需要接受确认；学生能否建项目由 `STUDENT_CAN_CREATE_PROJECT` 开关控制（默认允许）。
- 通知中心只有已读/未读，没有"确认/审批/签收"；Dashboard 的"需关注"仅提示不阻断。

高风险动作（删除项目、重新生成二维码、解绑微信、安全配置修改）只做**本人确认**（Confirm Dialog），不引入他人审批。不含工作流引擎/BPM/Redis/MQ。

多端一致：老师与学生 PC Web、手机 Web（响应式 <768 / 768–991 / ≥992）、微信小程序（`miniprogram/`）功能对齐；设备二维码（生成/绑定/下载/重生成旧码失效/扫码）与内网 HTTPS 见 `docs/intranet-https.md`。

## 技术栈

| 层 | 技术 |
| --- | --- |
| 前端 | Vue 3 + TypeScript + Vite + Element Plus + Pinia + Vue Router + Axios + ECharts + Day.js |
| 后端 | Python 3.12 + FastAPI + Pydantic v2 + SQLAlchemy 2 + Alembic + JWT (PyJWT) + pwdlib (argon2) |
| 数据库 | PostgreSQL 16（本地开发可用 SQLite，通过 `DATABASE_URL` 切换） |
| 部署 | Docker Compose（frontend / backend / postgres / nginx）；内网 HTTPS 方案见 `docs/intranet-https.md` |

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
- `docs/intranet-https.md` — 内网 HTTPS（Let's Encrypt DNS-01 + Nginx）
- `docs/backup_restore.md` — 备份恢复
- `docs/ai-assistant.md` — AI 助手：配置、权限、安全边界
- `docs/retrieval-architecture.md` — 检索引擎（Search 与 AI 共用）
- `docs/security.md` — 安全设计
- `miniprogram/README.md` — 微信小程序接入
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
