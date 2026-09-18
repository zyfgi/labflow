# FINAL_REPORT — 业务审计 / 测试收敛 / 配置中心 / 瘦身 / UI

> 基线 `e8a6829` → 本轮提交。一次性无人值守执行。历史报告已删除（Git 保留历史）。

## 1. Baseline

backend/app 74 文件 / 8750 LOC；tests 2709 LOC；frontend 7015 LOC；pytest 131；前端测试 6；
dashboard 29 queries；build 2799KB。详见 `docs/refactor-baseline.md`（含 before/after 表）。

## 2. 发现的业务 bug（审计结论 15 项）

private/project_members 语义重复；EQUIPMENT_ADMIN 经 membership/owner/assignee 旁路读科研数据；
设备域误用 is_staff；assignee 可 PATCH 任务全部字段；任务/里程碑状态无枚举校验；
done→reopen 未清 completed_at；任务可挂其他项目的里程碑/父任务、assignee 无角色校验（可 500）；
项目软删后子任务仍可直读；实验锁定对 PI 不彻底；approved 预约可被改期仍 approved；
未来预约把设备长期置 reserved；借用允许过去归还时间；维修状态机不完整；
due_checker 自定义时间源；实验编号测试永真断言；mutation schema 静默忽略未知字段。

## 3. 修复（全部带回归测试）

- **可见性三档真正分层**：private=PI/owner/manager；project_members=+成员；lab=+TEACHER/STUDENT。
  EQUIPMENT_ADMIN/GUEST 在 owner/member 判断**之前**直接拒绝科研域（含 Search/AI Retrieval/子任务）。
- **设备域角色拆分**：`EQUIPMENT_VIEW_ROLES = PI+EQUIPMENT_ADMIN` 看全部预约/借用；
  TEACHER/STUDENT 仅本人。设备管理员被加进 ProjectMember 也读不到科研数据（有测试）。
- **任务权限拆分**：PATCH 仅项目管理方（改 title/assignee/优先级等 metadata）；
  assignee 走 `/status` 与评论。`TaskStatusRequest.status` 严格枚举（非法 422）。
- **状态时间戳**：done→completed_at=now、progress=100；离开 done/cancelled 清 completed_at（reopen 测试）。
- **跨资源完整性**：milestone/parent 必须同项目；assignee 必须 active、非 EQUIPMENT_ADMIN/GUEST，
  private/project_members 项目还须是成员。非法一律 422，不再 500。
- **软删项目子任务封禁**：Scope 要求父项目未删；direct GET/评论 404；Search/AI 均不可见。
- **实验锁定 = 冻结**：锁定后 owner/manager/PI 全部不可改/传/删附件/删实验，仅 unlock 恢复。
- **预约状态机**：pending→approved/rejected/cancelled；approved→cancelled/completed；终态封闭。
  approved 被申请人改期 → 自动回 pending 并清审批字段（重新审批）。测试覆盖非法转换 400。
- **设备物理状态解耦**：approve/cancel 不再写 reserved；详情返回 current_booking/next_booking。
- **借用/维修完整性**：expected_return_time 必须未来（422）；维修转换表
  reported→processing/cancelled、processing→completed/cancelled，终态封闭，取消/完成后按剩余工单恢复设备状态。
- **due_checker** 统一用 `app.core.time`；实验编号测试改为 regex+序号递增；未知字段 422（StrictSchema）。

## 4. 测试体系

- 删除阶段性文件 `test_p0_hardening.py`、`test_refactor_p0.py`，规则并入领域文件。
- 新增：`factories.py`（6 个 API 级工厂）、`test_rbac_matrix.py`（角色×资源参数化）、
  `test_tasks.py`、`test_settings.py`；歧义断言（多结果都算成功）改为单一契约。
- 关键保护全部保留：SECRET_PROJECT_B_TOKEN 三层零泄漏、周报泄漏、注入边界、
  会话所有权、单次模型调用、锁定、预约冲突、RBAC。
- pytest 131 → **160 passed**；`pytest-cov` 分支覆盖 **78%**（权限/AI 安全/Settings 88–100%）。

## 5. 系统设置（可视化配置中心）

- 迁移 `b713192d`：单表 `system_settings`（id=1，config_json + encrypted_secrets）。
- `GET/PATCH /api/v1/system/settings`（仅 PI）+ `POST /system/settings/ai/test`。
- Runtime 可编辑：APP_NAME、APP_TIMEZONE(restart)、AI 全部参数、UPLOAD_MAX_MB、扩展名白名单。
  Bootstrap 只读展示：DATABASE_URL 密码脱敏、SECRET_KEY 仅显示 configured。
- **AI_API_KEY write-only**：Fernet（由 SECRET_KEY 派生）加密存储，GET 只返回
  `AI_API_KEY_CONFIGURED`；留空保留、传新值更新、clear_ai_api_key 清除；审计不记录 secret。
- AI 服务/限流/上下文/存储上传每次请求读取一次 runtime 配置，生效无需重启（时区除外，UI 已标注）。
- 前端 `/system/settings`（PI）：基础设置/AI 助手/存储/部署与安全 四 Tab，测试连接只显示 结果/模型/延迟。

## 6. UI 与瘦身

- MainLayout 改为**数据驱动菜单**（label/icon/route/roles 一套数组过滤），支持折叠、窄屏自动收起。
- 新增 `styles/tokens.css` 设计令牌；Dashboard KPI 数组驱动；删除无路由引用的 HomeView；
  阶段性注释（P0/Phase/PRD§）全仓清除；`ruff format` + `ruff check` 全绿。
- 删除 `docs/archive/` 历史执行报告。

## 7. 代码量（诚实说明）

旧业务生产代码净减约 380 行（Planner、权限双实现、设备状态同步、utcnow 重复、死 schema/helper/HomeView）。
但本轮**新增 Settings 功能约 675 行**（前后端）+ 新增回归测试约 900 行，加上 ruff format 换行展开，
backend/app 总 LOC 8750 → 10649、frontend 7015 → 7308。**未达"旧业务净减 8%"目标**，原因即上述；
旧代码的删减点均可 grep 复核（planner/staff 预约分支/reserved 同步等已不存在）。

## 8. SQL / 构建

dashboard 29 queries（保持）；projects/tasks/experiments 各 5（保持，含 5→50 行数据回归断言）；
ai/retrieve 10；build dist 2808KB（+9KB，Settings 页）。

## 9. 验证结果

```text
ruff check app tests        All checks passed
ruff format app tests       已执行
pytest -q                   160 passed
pytest --cov=app --cov-branch   78% branch
alembic current             b713192d (head)；fresh DB upgrade → 24 表全部建立
frontend typecheck          0 错误
frontend test               6 passed
frontend build              ✓ built
Docker                      本机无 Docker（延续环境限制），compose 已静态校验
```

## 10. Known Issues

1. 分支覆盖 78%，略低于 80% 目标；缺口集中在检索 members/weekly_reports 模块的少量分支。
2. Docker 本机不可用（无法 compose build/up），文件持续维护并通过 YAML 校验。
3. Playwright E2E 未引入（浏览器安装受限）；以 API 级业务回归 + Vitest 覆盖同等场景。
