# LabFlow V1 Final Report

> 生成时间：2026-09-17（无人值守一次性执行模式，Milestone 0 → 9 全部完成）
> 所有"执行结果"均为本机真实运行记录，非模板占位。

---

## 1. Completion Summary

**完成比例：Milestone 0–9 全部完成；PRD §54 停止条件清单 28/28 达成。**

- 核心域：认证/RBAC、成员与学习进度、周报闭环、项目与任务、实验记录（附件+锁定）、设备全生命周期（预约冲突/借还/维修）、PI/学生 Dashboard、通知/搜索/导出/审计日志 —— 全部真实数据库实现，无 Mock。
- 工程化：Alembic 迁移（fresh DB 一次建全 20 表）、幂等 seed、76 个后端测试全绿、前端生产构建通过、Docker Compose 四容器编排交付。
- 唯一环境限制：本机无 Docker 守护进程，`docker compose up` 无法本机启动验证（详见 §11）；compose/nginx/Dockerfile 已按规范交付并通过 YAML/配置一致性校验，本地验证改用「嵌入式 PostgreSQL 16.2 + uvicorn + Vite」真实运行等价完成。

## 2. Architecture

| 层 | 技术 |
| --- | --- |
| 前端 | Vue 3.5 + TypeScript + Vite 5 + Element Plus + Pinia + Vue Router + Axios + ECharts + Day.js + qrcode |
| 后端 | Python 3.12 + FastAPI + Pydantic v2 + SQLAlchemy 2 + Alembic + PyJWT + pwdlib(argon2) + openpyxl |
| 数据库 | PostgreSQL 16（生产）；SQLite（单测，`DATABASE_URL` 切换） |
| 部署 | Docker Compose：frontend / backend / postgres / nginx（唯一 :80 边界入口） |

详见 `docs/architecture.md`。

## 3. Implemented Modules

| 模块 | 内容 |
| --- | --- |
| 认证与用户 | JWT 登录/登出/me/改密；失败统一文案；首登强制改密提示；用户管理（角色/停用/重置） |
| 成员与学习 | 成员档案、成员概览聚合、技能定义/技能矩阵（0–4 级）、学习计划 CRUD |
| 周报 | draft→submit→review / return→resubmit 状态机；每人每周唯一；导师意见 |
| 项目任务 | 项目（可见性三级+软删除）、项目成员、里程碑、任务（子任务/状态机/评论）、逾期判定 |
| 实验记录 | 自动编号 EXP-YYYYMMDD-XXXX、全字段、附件上传/鉴权下载、lock/unlock（解锁写审计） |
| 设备 | 台账、预约（后端冲突检测）、借出归还、故障维修流程、设备二维码（显示+下载 PNG） |
| Dashboard | PI 看板（8 KPI+项目进度+成员动态+待办+最近动态，ECharts）、学生看板 |
| 系统辅助 | 站内通知（事件挂接+未读数）、全局搜索（5 类带权限过滤）、CSV/XLSX 导出（5 类带权限矩阵）、操作日志（PI）、每日到期检查器 |

## 4. Database

- 18 张业务表 + `task_comments` + `alembic_version`，fresh DB `alembic upgrade head` 一次建全（实测 20/20，missing: NONE）。
- PRD §18 约束全部落地：username/email/asset_no/experiment_no/project.code UNIQUE；ProjectMember、MemberSkill、WeeklyReport(member_id, week_start) 复合 UNIQUE；外键全带索引；status/due_date/project_id/user_id/member_id/equipment_id 高频索引。
- ER 图见 `docs/database.md`。
- 当前版本：`2085ac133de4 (head)`，`alembic current` 与 head 一致。

## 5. API Summary

约 70 个端点（`/api/v1` 前缀），分模块清单见 `docs/api.md`；交互式文档 `/api/docs`。统一 `{data,message}` 包装与分页结构。

## 6. Frontend Pages

登录页、Dashboard（PI/学生双形态）、成员列表/成员详情（7 Tabs）、技能矩阵、学习计划、项目列表/项目详情（概览/成员/里程碑/任务 Tabs + 实验活动占位已由实验页替代）、任务列表/任务详情（含评论）、实验列表/实验详情（编辑/附件/锁定）、设备台账/设备详情（预约+二维码）/预约/借用/维修、周报列表（学生写作+PI 审核）、通知中心、用户与角色（PI）、操作日志（PI）、个人设置。

状态色统一遵循 PRD §23（success/warning/danger/info/primary 语义映射）；列表均含 loading/empty/筛选/分页。

## 7. RBAC and Permissions

- 角色五类：PI / TEACHER / STUDENT / EQUIPMENT_ADMIN / GUEST，全部后端强制（`require_roles` + 资源函数）。
- 项目级权限 = 角色 + `visibility` + 项目成员 + owner：private（owner+PI）、project_members（成员）、lab（全实验室）；学生越权读取实测 403。
- 资源属主：周报/学习计划/技能/任务状态仅本人（+管理方）可改；锁定实验仅 PI 可解锁。
- 设备管理边界：台账/维修处理 = PI+设备管理员；预约审批 = PI+设备管理员；上报/借用/预约 = 全体成员。

## 8. Tests

### Backend
```text
command:  cd backend && .venv/Scripts/python -m pytest -q
result:   76 passed, 145 warnings in 85.20s
覆盖：认证/权限/周报状态机/任务/实验编号与锁定/设备预约冲突/借用归还/维修/Dashboard/通知/搜索/导出/审计/到期检查器幂等
```

### Frontend
```text
command:  cd frontend && npm run build
result:   ✓ built in 9.92s（生产构建，无报错；chunk 1,128.59 kB / gzip 374.27 kB）
```

### Database
```text
command:  alembic upgrade head（fresh sqlite DB） + alembic current（PG）
result:   20 tables created, missing: NONE；PG current = 2085ac133de4 (head)
```

### Docker
```text
command:  docker compose up -d --build
result:   本机无 Docker 守护进程，无法实际启动（已用 PyYAML 校验 compose 语法与
          服务定义；四容器/卷/健康检查/127.0.0.1 绑定/debug=false 均已确认）。
          本地等价验证：嵌入式 PostgreSQL 16.2 + uvicorn + Vite 全链路真实运行。
```

## 9. End-to-End Verification

全部基于 seed 数据、真实 HTTP 调用（uvicorn :8000）：

| 流程 | 结果 |
| --- | --- |
| E2E-1 PI：登录→看板→建项目(id=4)→加学生→建里程碑→建任务(id=19) | ✅ 全部 200/201 |
| E2E-2 学生科研：phd02 建实验(EXP-20260917-0001)→填结果→传附件(元数据入库)→更新进度 | ✅ |
| E2E-3 周报：master05 提交→admin 退回(带意见)→学生改→重提→admin 审核通过；reviewed 后编辑 400 | ✅ |
| E2E-4 设备：master01 预约 A(10-12)批准→冲突 B(11-13) 409→相邻 C(12-14) 201→借出(borrowed)→归还(returned) | ✅ |
| E2E-5 权限：改他人周报 403 / 改设备档案 403 / 非成员读项目 403 / 改锁定实验 403 | ✅ 四项全部拦截 |

Dashboard 实测（seed 数据）：成员 12、活跃项目 2、周报提交率 33%（3/9）、逾期任务 11、待审周报 3、待批预约 4、故障设备 1、今日预约 1 —— 全部来自 SQL 聚合。

## 10. Security Checks

```text
[x] .env 未提交（git check-ignore 确认 backend/.env 被忽略）
[x] 仓库无真实密钥：SECRET_KEY 全部为占位符/测试值；seed 密码仅开发用且首登强制改密
[x] 密码仅存 argon2 哈希（pwdlib）；登录失败统一文案，不泄露用户名存在性
[x] JWT 有效期 24h（可配置）；未登录访问保护 API → 401
[x] 上传文件名清理 + UUID 前缀 + 扩展名白名单 + 100MB 限额 + 路径穿越防护
[x] 附件下载仅经鉴权 API（FileResponse 流式），静态目录不暴露上传件
[x] CORS 白名单可配置（CORS_ORIGINS）
[x] compose 生产环境 LABFLOW_DEBUG=false；数据库仅绑定 127.0.0.1
[x] ORM 全程参数化查询；关键操作写审计日志
```

## 11. Known Issues

1. **Docker 本机不可用**：开发机无 Docker 守护进程，`docker compose up` 未实际执行。风险主要在镜像构建细节（网络、平台），compose 定义已通过 YAML 解析与逐项审查（4 服务、healthcheck、依赖顺序、卷、端口绑定）。在有 Docker 的机器上按 README 步骤即可部署。
2. **周报状态机为单向**：reviewed 后不可再改（需线下协商），V1 按 PRD 实现，未提供"撤回审核"。
3. **通知为站内实时写入**：到期类通知依赖每日 `due_checker`（compose 内可加 cron），未引入消息队列（符合 V1 边界）。
4. **项目详情页「活动」Tab**：活动流聚合在 Dashboard 呈现；项目详情 Tab 显示项目任务与实验（实验 Tab 跳转实验列表），独立项目活动流水列为 V2 增强。
5. **Git Bash curl 中文 body** 编码受限：仅影响手工冒烟方式，pytest 与前端 axios 无此问题。

## 12. Deferred V2 Features

按 PRD §2.2/§35 未实现：CAS/OAuth 统一认证、微信小程序/App、财务报销、采购审批、耗材 ERP、论文/专利全过程管理、GPU 调度、LIMS、AI 问答、自动科研评分、复杂甘特图、WebSocket 协同、消息队列、微服务、科研成果/知识库模型（数据结构已预留接入）。

## 13. How to Run

```bash
cd labflow
cp .env.example .env        # 修改 SECRET_KEY 与数据库密码
docker compose up -d --build
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.seed
# 访问 http://localhost  （API 文档 /api/docs）
```

本地开发（无 Docker）：见 README「本地开发」；到期检查：`python -m app.due_checker`。

## 14. Demo Accounts

| 用户名 | 角色 | 姓名 | 密码（仅开发） |
| --- | --- | --- | --- |
| admin | PI | 张建国 | `Labflow@123` |
| teacher01 | TEACHER | 李弘 | 同上 |
| phd01 / phd02 | STUDENT(博士) | 王晓东 / 刘雨欣 | 同上 |
| master01–master05 | STUDENT(硕士) | 陈晨/赵磊/孙悦/周涛/吴静 | 同上 |
| under01 / under02 | STUDENT(本科) | 郑云 / 冯凯 | 同上 |
| equipadmin | EQUIPMENT_ADMIN | 徐明 | 同上 |

Seed 规模：12 用户、4 项目、8 里程碑、19 任务、8 周报、9 实验、10 技能/53 成员技能、11 学习计划、6 设备、9 预约、4 借用、2 维修。所有账号 `must_change_password=true`，首次登录系统提示修改。

## Git Checkpoints

```text
03584b8 chore: initialize labflow project
47d7f2d feat: authentication and user management
df8d692 feat: member and learning management
b185478 feat: weekly report workflow
1a6458e feat: project and task management
df26b63 feat: experiment management
289e8ff feat: equipment management
2e4a7bd feat: dashboards
219fa5a feat: notifications search and export
<final> chore: production hardening and documentation
```

---

# 下一阶段报告：代码整改 + 实验室 AI 助手

> 执行模式：一次性无人值守（Phase 1–14）。所有结果为真实执行记录。

## 1. 原始 baseline

- git clean @ fbb3d87；后端 76 passed（86s）；前端 build ✓ 13.49s；alembic = 2085ac133de4；无 typecheck/lint/test 配置
- 本机无 Docker（延续 V1 限制）

## 2. 发现的问题（整改前代码审查）

1. `/search`：先 LIMIT 候选 → Python 循环 can_read → 再过滤截断；Task/Experiment 每条 `db.get(Project)` → N+1、候选窗口被无权限结果占用
2. EQUIPMENT_ADMIN 被视为 staff：可看成员档案/学习计划/技能/周报并参与周报审核
3. 无生产配置校验；且 compose 传的 `LABFLOW_DEBUG=false` 因缺少环境变量别名映射实际未生效
4. seed 在生产可用固定 demo 密码；无独立 create-admin
5. 权限条件在 projects/tasks/experiments/search 各自复制，AI 接入会扩大风险

## 3. 修复的问题

以上 5 项全部修复：统一 Scope（access.py）+ Search/列表/导出复用；设备管理员成员域 403；production fail-fast + 环境别名；ALLOW_DEMO_SEED + `python -m app.cli create-admin`；新增 15 项 P0 测试。

## 4. 修改的架构

新增两层：`services/retrieval/`（Search 与 AI 共用的权限检索引擎）与 `services/ai/`
（provider 抽象 / prompts / context builder / 限流 / 编排）。AI 数据流：
问题 → (可选 LLM Planner，仅问题文本) → SQL 级权限检索 → 白名单字段上下文（≤30k 字符）
→ OpenAI-compatible API → 回答 + 后端生成来源链接。LLM 无数据库访问、无独立权限、只读。

## 5. 数据库 migrations

`bf384965486a`：ai_conversations / ai_messages / ai_request_logs（含 downgrade）；
fresh DB `upgrade head` → 23 表全部建立（含升级前后校验）。

## 6. 新 API

```
POST /api/v1/ai/chat          POST /api/v1/ai/retrieve（调试，dev 开放/生产仅 PI）
GET/POST /api/v1/ai/conversations   GET/DELETE /api/v1/ai/conversations/{id}   GET /api/v1/ai/status
```

## 7. Retrieval Engine 设计

四层：实体解析（DB 实体名回查问题）→ 规则意图（12 类 intent + 7 种时间预设 + mine_only）
→ 关键词 ILIKE 加权（编号+6/标题+4/结论+3/方法+2；CJK 2-gram）→ 结构化直查（逾期任务等）。
安全回退：仅开放性自然语言问题在关键词 0 命中时按 Scope 宽松召回；实体指向/精确 token 查询不回退；
日期敏感源保留时间过滤。权限全部在 SQL Scope 内（与 Search/列表/导出共享 access.py）。
详见 `docs/retrieval-architecture.md`。

## 8. AI Provider 设计

`LLMProvider` Protocol + `OpenAICompatibleProvider`（httpx；connect 10s、总超时 AI_TIMEOUT_SECONDS；
401/403→AUTH、429→RATE_LIMIT、5xx→ERROR、超时→TIMEOUT、解析失败→RESPONSE_INVALID）+
`FakeLLMProvider`（捕获 messages，可注入错误）。切换厂商只改 AI_BASE_URL/AI_API_KEY/AI_MODEL。
限流 10/min + 100/day（应用内，可配）。

## 9. AI Assistant 页面

`/ai`：左侧历史对话（新建/删除/切换），右侧消息流 + 来源卡片（点击跳转原始页面）+
角色化推荐问题 + 友好错误展示；导航新增「AI 助手」。构建通过（见下）。

## 10. 权限测试

- `tests/test_p0_hardening.py`（15）：设备管理员访问成员/学习计划/周报/审核一律 403、设备域 201/200
- `tests/test_ai_permissions.py`（6）：Project B private + Student A 越权全套（见 §11）
- Search Scope 回归：学生搜索私项目编号 → 0 结果；PI → 命中

## 11. 敏感数据泄漏测试（P0）

`SECRET_PROJECT_B_TOKEN_9F83A` 埋入 Project B 的 description/task.description/experiment.conclusion：

```text
/search?q=<token>（Student A）        → 全部分类 0 结果 ✅
/ai/retrieve q=<token>（Student A）   → 0 hits（PI 控制组 >0，证明数据存在）✅
FakeLLMProvider 捕获全部 messages     → 不包含 token（Student A 广泛提问）✅
Student B 周报私有内容                → 不进入 Student A 的 LLM context ✅
响应中无"无权限"侧信道措辞 ✅
```

## 12. Prompt Injection 测试

实验 conclusion 写入 "Ignore previous instructions..."：仅以 `<labflow_source>` 证据形式出现在
chat 上下文中；System Prompt 含 untrusted 声明；planner 调用零业务数据；私有项目 token 不出现。

## 13. Backend pytest 结果

```text
command: pytest -q        result: 121 passed（2:16）
（baseline 76 → 整改 91 → AI 阶段 121）
```

## 14-15. Frontend typecheck / build 结果

```text
command: npm run typecheck   result: exit 0（0 错误，vue-tsc）
command: npx vitest run      result: 6 passed（AI store/api/来源渲染/会话状态）
command: npm run build       result: ✓ built in 14.04s
```

## 16. Docker 结果

本机无 Docker 守护进程（无法 compose build/up —— 与 V1 相同的环境限制）。
compose YAML 解析通过：4 服务、postgres 仅绑 127.0.0.1、backend healthcheck、
生产 debug=false。本地以「嵌入式 PG 16 + uvicorn + Vite + 本地 OpenAI-compatible 桩」完成等价 E2E。

## 17. E2E 结果（真实 HTTP）

```text
/ai/retrieve "UKF相关实验结果"        → 5 hits，TOP1=UKF-EKF 低附着对比实验（127ms）
/ai/chat（桩模型，完整链路）           → conversation_id=1 持久化、回答、来源 [/tasks/2]、usage tokens
第二轮对话（conversation_id=1 复用）   → 每轮重新检索（AIRequestLog 两条 success，latency 339/44ms）
落库验证                              → ai_conversations/ai_messages/ai_request_logs + AuditLog ai_chat×2
AI 未启用                             → 503 {"code":"AI_DISABLED"}（前端显示友好文案）
```

## 18. 当前已知问题

1. Docker 本机不可用（环境限制）；compose 交付并静态校验。
2. Query Planner 依赖模型输出受限 JSON，弱模型下可能频繁回退规则解析（不影响可用性）。
3. 检索为 ILIKE 子串匹配，未做分词/语义检索（按方案 V1 不引入向量库）。
4. 限流为单实例内存实现，多实例部署需换 Redis。

## 19. 未完成项

无（方案 §66 完成定义逐项达成）。SSE 流式输出按方案建议留待后续（权限>检索>回答>来源>streaming）。

## 20. 后续 V2 建议

pgvector 附件/知识库语义检索；SSE 流式；AI 会话管理页（重命名/置顶）；
按角色的 AI 使用统计面板；多实例 Redis 限流；检索召回评测集自动化。
