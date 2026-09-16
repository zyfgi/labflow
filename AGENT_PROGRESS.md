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

---

# Milestone 1 — 认证与用户

## Completed

- 模型：`User`、`MemberProfile`（含唯一约束/外键/索引）、`AuditLog`、`Notification`（表已建，M8 启用逻辑）
- Alembic 初始化 + 初始迁移（已应用到 PostgreSQL 16）
- JWT 认证（登录/登出/me/改密），登录失败统一提示不泄露用户名是否存在
- RBAC 依赖（`get_current_user` / `require_roles` / `require_pi` / `require_teacher_or_pi`），全部后端校验
- 用户管理 API（列表/筛选/分页、创建、详情、更新、角色变更审计）
- `must_change_password` 首登改密提示
- seed：12 个账号（1 PI + 1 教师 + 9 学生 + 1 设备管理员）+ MemberProfile
- 前端：登录页、MainLayout（角色化导航/面包屑/用户菜单）、路由守卫、axios 拦截器（401 跳转）、用户管理页、个人设置页、统一状态色常量

## Files Changed

- `backend/app/models/{base,user,system,enums,__init__}.py` `backend/app/core/{deps,responses}.py`
- `backend/app/api/v1/{auth,users}.py` `backend/app/api/__init__.py` `backend/app/schemas/user.py`
- `backend/alembic/`（env.py, script.py.mako, alembic.ini, 初始迁移 `0ee62f05bcbb`）
- `backend/app/seed.py` `backend/tests/{conftest,test_auth,test_permissions}.py` `backend/pytest.ini`
- `frontend/src/{api/{client,auth,users}.ts, stores/auth.ts, utils/{constants,datetime}.ts, types/index.ts}`
- `frontend/src/{layouts/MainLayout.vue, views/{LoginView,DashboardView,ProfileView}.vue, views/system/UsersView.vue, router/index.ts}`

## Database Changes

- 新表：`users` `member_profiles` `audit_logs` `notifications`（唯一约束 username/email、(member_id,week_start) 等后续迁移随模块加入；外键均带索引）

## API Added

```
POST /api/v1/auth/login | logout   GET /api/v1/auth/me   POST /api/v1/auth/change-password
GET/POST /api/v1/users   GET/PATCH /api/v1/users/{id}   GET /api/v1/users/options
```

## Tests

Command: `.venv/Scripts/python -m pytest -q`
Result: **18 passed**（登录成功/错密码/未知用户同文案/未登录 401/改密流/PI 建用户/重名 409/改角色/学生越权 403/停用账号 401）

## Manual Verification（真实 HTTP，seed 数据）

```text
admin 登录 → 200 + JWT ✅
/auth/me → 用户信息 ✅
错误密码 → 401 {"detail":"用户名或密码错误"} ✅（与未知用户文案一致）
无 token 访问 /users → 401 ✅
frontend build ✓ 5.40s
```

## Known Issues

- pydantic `EmailStr` 拒绝保留域名（.local 等），已换成轻量校验便于校园内网域名

## Next Step

Milestone 2：Skill/MemberSkill/LearningPlan + 成员列表/详情/技能矩阵/学习计划页面
