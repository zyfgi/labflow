# AGENTS.md — LabFlow Agent 维护手册

> 后续 AI Agent / 开发者先读这一份（约 200 行）。历史执行记录在 `docs/archive/`。

## 项目是什么

高校科研实验室管理系统（5–50 人课题组）：成员 → 周报 → 项目/任务 → 实验记录 → 设备 → 看板，
外加一个**只读** AI 助手（本地权限检索 + 外部 OpenAI-compatible 模型）。

技术栈：Vue 3 + TS + Vite + Element Plus + Pinia｜FastAPI + SQLAlchemy 2 + Alembic + PostgreSQL 16。

## 常用命令

```bash
# 后端（backend/ 下）
.venv/Scripts/python -m pytest -q          # 全量测试（Windows 路径；Linux 用 .venv/bin/）
.venv/Scripts/python -m alembic upgrade head
.venv/Scripts/python -m app.seed           # 开发 demo 数据（生产默认拒绝）
.venv/Scripts/python -m app.cli create-admin
.venv/Scripts/python -m app.due_checker    # 每日到期检查
.venv/Scripts/python -m ruff check app/ --select F401,F811,F841
.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000

# 前端（frontend/ 下）
npm run typecheck     # vue-tsc --noEmit
npm test              # vitest run
npm run build
npm run dev           # :5173，/api 代理到 :8000
```

本地数据库：默认用 `backend/.env` 的 `DATABASE_URL`（当前指向嵌入式 PG 16：
二进制 `C:\Users\14993\.labflow_pginstall`，数据 `C:\Users\14993\.labflow_pgdata`，
启动 `pg_ctl -D C:\Users\14993\.labflow_pgdata start`）。Windows 上嵌入式 PG 必须
纯 ASCII 路径 + `--locale=C`。单测自动用 SQLite（conftest 设环境变量）。

## 目录职责

```text
backend/app/
├── core/            config（含生产 fail-fast）/ time（唯一时间源）/ security / deps / responses
├── models/          SQLAlchemy 模型 + enums.py 集中常量
├── schemas/         Pydantic 请求/响应
├── api/v1/          路由层：只做参数校验、调 service/模型、组装响应
├── permissions/     ★ 唯一权限源：__init__（角色/成员数据）+ projects.py（项目/任务 Scope）
├── services/
│   ├── retrieval/   Search 与 AI 共用的本地检索引擎（engine/intent_parser/entity_resolver/各数据源）
│   └── ai/          provider 抽象 / prompts / context_builder / service / rate_limit / errors
├── storage/         StorageService（文件上传唯一入口）
└── seed.py seed_data.py cli.py due_checker.py
frontend/src/        api/（axios 模块）stores/ views/ layouts/ router/ utils/ types/
docs/                架构/数据库/API/部署/备份/AI/检索/安全 说明 + archive/（历史报告）
```

## 硬性规则（违反 = bug）

1. **权限逻辑只能存在于 `app/permissions/`**（对象级 `can_*` + 查询级
   `visible_project_ids_subquery / apply_project_read_scope / visible_task_scope_conditions`）。
   任何路由、Search、导出、Dashboard、AI Retrieval 都不得复制或绕过它。
2. **Router 不允许 per-row `db.get()`**：列表端点必须批量取关联（一次 IN 查询 + dict 映射），
   `tests/test_query_counts.py` 用 SQL 计数器守护（数据 ×10，查询数不得增长 >2）。
3. **Retrieval 不允许绕过权限 Scope**；AI context 只能来自 Retrieval 输出；
   LLM 不能访问数据库，AI 全程只读（不创建/修改/审批任何业务数据）。
4. **正常 AI 问答只调用一次模型 API**（无 Planner；问题→规则解析→检索→一次 LLM→答案+来源）。
5. **不允许静默吞 Exception**（`except Exception: continue` 禁止）；程序错误要暴露，
   只捕获明确可恢复的领域异常（如 `AIError`）。
6. **不为未来功能提前抽象**；helper 只在 ≥2 处真实复用时才抽取；
   无调用者的函数/schema/组件直接删除（`ruff --select F401,F811,F841` + grep + tsc 验证）。
7. **时间只用 `app/core/time.py`**：业务口径 `app_today/app_now/week_start_of/time_range`，
   数据库时间戳 `utcnow`（全部 naive UTC）。禁止直接 `date.today()/datetime.now()`。
8. **安全测试不可删**：SECRET 泄漏三层断言、周报泄漏、注入边界、会话所有权、
   实验锁定、预约冲突、RBAC（见"关键测试"）。
9. 响应统一 `{data, message}` + 分页 `{items,total,page,page_size}`；错误 `{"detail": ...}`；
   AI 错误为 `{code, message}`（code 可外露，内部细节不外露）。
10. 状态色语义统一（success=完成/可用，warning=待审/受阻，danger=逾期/故障，info=草稿/归档），
    常量在 `frontend/src/utils/constants.ts`。

## 权限模型速查

- 角色：PI（全部）/ TEACHER（教学）/ STUDENT / EQUIPMENT_ADMIN（仅设备域）/ GUEST（最小）。
- 项目读 = PI ∪ owner ∪ 在册成员 ∪（`visibility=lab` 且角色 ∈ {TEACHER, STUDENT}）。
  **EQUIPMENT_ADMIN 与 GUEST 不因 lab 可见性读到任何项目/任务/实验/周报/成员档案。**
- 项目管理 = PI ∪ owner ∪ owner/manager 成员。实验创建 = PI ∪ owner ∪ 在册成员（仅 lab 可见不行）。
- 实验锁定后对普通成员冻结（编辑/传/删附件均 403），PI 可解锁并写审计。
- 周报：PI/教师全量；学生仅本人（含 AI 检索）。AI 会话：严格本人，PI 也不例外。

## AI 数据流

```text
问题 → parse_query（规则意图+时间+mine_only） → entity_resolver（每类实体一次查询）
→ RBAC Retrieval（SQL Scope，安全回退仅限 overview/member_progress）
→ build_context（白名单字段 JSON，≤AI_MAX_CONTEXT_CHARS）
→ 一次 OpenAI-compatible 调用（密钥仅在 backend）
→ 答案 + sources[]（后端生成 url）
```

配置全在 `.env`（`AI_*`，见 `.env.example`）；`AI_ENABLED=false` 时 `/ai/chat` 返回 503 AI_DISABLED。

## 数据库原则

- 迁移只经 Alembic（`alembic upgrade head`）；模型增删后 `alembic revision --autogenerate`。
- 通用类型（String/Integer/JSON…），保证 PG（生产）与 SQLite（测试）双跑。
- 关键唯一约束：username/email、project.code、experiment_no、equipment.asset_no、
  (member_id, week_start)、(project_id, user_id)、(member_id, skill_id)。
- 软删除（deleted_at）：projects/tasks/experiments/equipment；其余硬删除。
- 全表 created_at/updated_at；关键操作写 audit_logs。

## 关键测试（不可删除）

```text
test_p0_hardening.py     设备管理员隔离 / production fail-fast / seed 守卫
test_ai_permissions.py   SECRET_PROJECT_B_TOKEN_9F83A：search/retrieve/LLM payload 三层 0 泄漏
test_ai_injection.py     注入指令只能作为 JSON source 证据；单次模型调用
test_ai_chat.py          会话所有权（PI 也不可读他人）/ 错误脱敏 / 限流 / 空结果不调模型
test_query_counts.py     列表与 Dashboard 的 SQL 数量不随数据量增长
test_equipment.py        预约冲突（重叠 409、相邻允许）/ 借还 / 维修
test_auth.py test_permissions.py test_projects.py test_weekly_reports.py test_experiments.py
```

## 禁止事项

- 新增 LangChain/LlamaIndex/向量库/本地模型/消息队列/微服务（V2 再议）。
- AI 写业务数据、SQL Agent、自主工具调用。
- 前端持有模型 API Key 或直连模型厂商。
- 把未过滤数据发给模型；用"有数据但无权限"类话术回复（侧信道）。
- 提交 `.env`/真实密钥/上传文件；`storage/*` 与 `*.db` 均已 gitignore。
