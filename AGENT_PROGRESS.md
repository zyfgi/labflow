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

---

# Milestone 2 — 成员与学习进度

## Completed

- 模型：Skill / MemberSkill（(member_id,skill_id) 唯一）/ LearningPlan；同时完成全部核心域模型建表迁移（projects/milestones/tasks/weekly_reports/experiments/equipment 等一次迁移到位，API 按后续里程碑启用）
- API：成员列表/详情/更新/overview 聚合、`/members/me`、技能 CRUD、成员技能读写（学生仅限本人）、学习计划 CRUD（学生仅限本人；staff 可查看全部）
- 权限：学生不能看成员列表/他人档案；只能编辑自己的学习计划与技能（后端强制）
- seed：10 个技能项 + 53 条成员技能 + 11 条学习计划
- 前端：成员列表、成员详情（概览/学习计划/技能 Tabs，后续 Tab 占位）、技能矩阵（可点击单元格打分）、学习计划页；路由级角色守卫

## Files Changed

- `backend/app/models/{learning,project,report,experiment,equipment}.py`、`app/models/__init__.py`
- `backend/app/api/v1/{members,skills,learning_plans}.py`、`app/api/__init__.py`
- `backend/app/schemas/{member,learning}.py`、`backend/app/permissions/__init__.py`
- `backend/alembic/versions/771322dcc366_core_domain_tables.py`、`backend/app/seed_data.py`
- `backend/tests/test_members.py`
- `frontend/src/api/{members,learning}.ts`、`views/member/{MembersView,MemberDetailView,SkillsMatrixView,LearningPlansView}.vue`、`components/{LearningPlanList,MemberSkillPanel}.vue`、`router/index.ts`

## Database Changes

- 新表：skills / member_skills / learning_plans / projects / project_members / milestones / tasks / weekly_reports / experiments / experiment_attachments / equipment / equipment_bookings / equipment_borrows / equipment_maintenance

## API Added

```
GET /members  POST /members  GET/PATCH /members/{id}  GET /members/{id}/overview  GET /members/me
GET/POST /skills   GET/PUT /members/{id}/skills
GET/POST /learning-plans  PATCH/DELETE /learning-plans/{id}
```

## Tests

Command: `.venv/Scripts/python -m pytest -q`
Result: **31 passed**（成员列表权限/他人档案 403/overview、技能 CRUD 与越权、学习计划本人限定/PI 可查可改/非法状态 422）

## Manual Verification（seed 数据，真实 HTTP）

```text
PI /members → total: 12 ✅
master01 /learning-plans → 仅自己 2 条计划 ✅
/skills → 10 项 ✅
frontend build ✓ 10.88s
```

## Known Issues

- 成员详情页的周报/项目/任务/实验 Tabs 在对应里程碑完成后启用（当前禁用态占位）

## Next Step

Milestone 3：周报 draft→submit→review→return 闭环 + 通知挂接

---

# Milestone 3 — 周报闭环

## Completed

- WeeklyReport 状态机：draft → submitted → reviewed；submitted → returned →（学生修改）→ 重新提交
- 每人每周唯一（member_id, week_start DB 唯一约束 + service 409）；week_start 自动归一到周一
- submitted 后学生不能修改（400）；审核/退回仅 PI/教师（403）；review_comment 全程可追溯
- 通知挂接：提交→通知全体 PI/教师；审核/退回→通知学生（Notification 表真实写入）
- seed：7 条周报（覆盖全部 4 种状态）
- 前端：周报列表（staff 可按成员/状态筛选）、学生写/编辑/提交周报表单、PI 通过/退回（带意见）、详情含导师意见

## Files Changed

- `backend/app/api/v1/weekly_reports.py`、`app/schemas/report.py`、`app/models/report.py`（加 member relationship）
- `backend/app/seed_data.py`、`backend/tests/test_weekly_reports.py`
- `frontend/src/api/reports.ts`、`views/report/WeeklyReportsView.vue`、`router/index.ts`

## API Added

```
GET/POST /weekly-reports  GET/PATCH /weekly-reports/{id}
POST /weekly-reports/{id}/submit|review|return   GET /weekly-reports/me/current
```

## Tests

Command: `.venv/Scripts/python -m pytest -q`
Result: **39 passed**（新增 8：草稿创建/周一归一/同周 409/完整审核流/退回重交流/学生越权 403/staff 全量列表/编辑锁定）

## Manual Verification（真实 HTTP，seed 账号 master05/admin）

```text
创建草稿 id=8 → submit: submitted ✅
PI return → returned | please add data ✅
学生修改 + resubmit → submitted ✅
PI review → reviewed | ok passed ✅
reviewed 后学生编辑 → 400 ✅
```

## Known Issues

- Git Bash curl 发送中文 JSON 有编码问题（shell 限制）；pytest 与前端 axios 均正常

## Next Step

Milestone 4：Project/ProjectMember/Milestone/Task + 项目级权限

---

# Milestone 4 — 科研项目与任务

## Completed

- Project CRUD（软删除）+ ProjectMember（唯一约束，owner 加入保护）+ Milestone + Task（软删除）+ TaskComment（任务详情评论/活动）
- 项目级权限（RBAC + visibility + 成员资格 + owner 综合）：
  - PI 全部可见；private/project_members 仅成员可见；lab 全实验室可见；GUEST 仅明确授权
  - 管理权 = PI/owner/项目 manager；任务编辑权 = 项目管理方 + assignee/creator
- 通知：任务分配/项目加入（Notification 真实写入）
- 任务状态机：done → progress 100% + completed_at；逾期判定（due_date < today 且未完成）
- seed：3 个项目（车辆参数在线估计/轮胎力在线估计/横摆稳定性控制）+ 8 个里程碑 + 18 条任务（含逾期/已完成/受阻）
- 前端：项目列表、项目详情（概览/成员/里程碑/任务 Tabs + 权限化操作）、任务列表（只看我的/筛选）、任务详情（状态更新/进度/评论）

## Files Changed

- `backend/app/models/project.py`（+TaskComment）、`app/schemas/project.py`、`app/api/v1/{projects,tasks}.py`、`app/permissions/projects.py`
- `backend/alembic/versions/2085ac133de4_task_comments.py`、`app/seed_data.py`、`tests/test_projects.py`
- `frontend/src/api/{projects,tasks}.ts`、`components/TaskFormDialog.vue`、`views/project/{ProjectsView,ProjectDetailView}.vue`、`views/task/{TasksView,TaskDetailView}.vue`、`utils/constants.ts`、`router/index.ts`

## Database Changes

- 新表：task_comments（其余域表在 M2 已建）

## API Added

```
GET/POST /projects  GET/PATCH/DELETE /projects/{id}
GET/POST /projects/{id}/members  DELETE /projects/{id}/members/{user_id}
GET/POST /projects/{id}/milestones  PATCH/DELETE /milestones/{id}
GET/POST /tasks  GET/PATCH/DELETE /tasks/{id}  POST /tasks/{id}/status
GET/POST /tasks/{id}/comments
```

## Tests

Command: `.venv/Scripts/python -m pytest -q`
Result: **51 passed**（新增 12：项目创建/编号重复 409/private 403/lab 可读/学生列表隔离/PI 全可见/成员不可改项目/里程碑完成/软删除/任务逾期判定/越权 403/评论/分配通知）

## Manual Verification（真实 HTTP，seed 数据）

```text
PI 建项目 id=4 → 加成员 under02 → 建里程碑 → 建逾期任务 id=19 ✅
成员学生读项目 → 200 ✅；非成员学生 → 403 ✅
under02 /tasks?mine=true → status: todo | overdue: True ✅
frontend build ✓ 6.99s
```

## Known Issues

- 项目详情「实验」「活动」Tabs 在 M5/M8 启用

## Next Step

Milestone 5：Experiment/实验编号/附件上传/StorageService/lock/unlock

---

# Milestone 5 — 实验记录

## Completed

- Experiment（软删除）+ ExperimentAttachment（DB 元数据 + 本地文件存储）
- experiment_no 自动生成 `EXP-YYYYMMDD-XXXX`（按日递增 + 唯一约束）
- StorageService 统一封装：文件名清理（去路径成分+非法字符替换）、UUID 前缀、扩展名白名单、100MB 可配置上限、路径穿越防护（resolve 后必须位于根目录内）、空文件拒绝
- lock/unlock：锁定后学生（非管理方）不能修改/上传；解锁仅 PI/项目负责方并写审计日志
- 附件下载走鉴权 API（FileResponse 流式），不做静态目录暴露
- 前端：实验列表、实验详情（全字段编辑 + 可追溯信息区 + 附件上传/下载/删除 + 锁定状态）
- seed：8 条实验（覆盖 completed/running/draft/failed、含锁定样例）

## Files Changed

- `backend/app/storage/__init__.py`、`app/schemas/experiment.py`、`app/api/v1/experiments.py`、`app/core/config.py`（白名单）、`app/seed_data.py`、`tests/test_experiments.py`
- `frontend/src/api/experiments.ts`、`components/ExperimentFormDialog.vue`、`views/experiment/{ExperimentsView,ExperimentDetailView}.vue`、`router/index.ts`

## API Added

```
GET/POST /experiments  GET/PATCH/DELETE /experiments/{id}
POST /experiments/{id}/lock|unlock|attachments
DELETE /experiment-attachments/{id}  GET /experiment-attachments/{id}/download
```

## Tests

Command: `.venv/Scripts/python -m pytest -q`
Result: **57 passed**（新增 6：编号自增/非成员 403/owner 更新/锁定禁止编辑+PI 解锁/附件上传下载与扩展名检查/锁定拒绝上传）

## Manual Verification（真实 HTTP，phd02/admin）

```text
学生建实验 → EXP-20260917-0001 ✅
更新结果 → completed ✅
上传附件 → {"id":1,"file_size":10,...} ✅
PI 锁定 → is_locked: True ✅
学生编辑 → 403 ✅
PI 解锁 → is_locked: False ✅
```

## Known Issues

- 无（M2 遗留的 config 循环导入与文件拼接问题已修复）

## Next Step

Milestone 6：Equipment/Booking(冲突)/Borrow/Maintenance/二维码
