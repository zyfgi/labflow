# Refactor Baseline（业务审计 + 测试收敛 + Settings + 瘦身 + UI）

基线 commit：`e8a6829`

## Before（本轮开始时）

| 指标 | 值 |
| --- | --- |
| backend/app 文件数 / LOC | 74 / 8750 |
| backend/tests LOC | 2709 |
| frontend/src 文件数 / LOC | 51 / 7015 |
| frontend/tests LOC | 127 |
| pytest | 131 passed |
| frontend tests | 6 passed |
| frontend build（dist） | 2799 KB |
| GET /projects SQL queries（50 行） | 5 |
| GET /tasks SQL queries | 5 |
| GET /experiments SQL queries | 5 |
| GET /dashboard/pi SQL queries | 29 |
| POST /ai/retrieve SQL queries | 8 |
| AI 问答模型调用次数 | 1 |

## After（本轮结束）

| 指标 | 值 | 变化 |
| --- | --- | --- |
| backend/app 文件数 / LOC | 见 git diff stat | |
| backend/tests LOC | | |
| frontend/src LOC | | |
| pytest | | |
| frontend tests | | |
| build（dist） | | |
| dashboard SQL queries | | |
| branch coverage | | |

## 已知业务问题（审计结论，对应修复）

1. `private` 与 `project_members` 语义几乎相同（成员两者皆可读）。
2. EQUIPMENT_ADMIN 可通过 membership/owner/assignee 旁路获得科研数据。
3. 设备域用 `is_staff`（PI+TEACHER）判定"看全部预约/借用"，设备管理员反而看不到全部。
4. assignee 可 PATCH 任务全部字段（title/assignee/priority 等）。
5. `TaskStatusRequest.status`、Milestone 状态无枚举校验。
6. done → in_progress 重新打开时 `completed_at` 未清理。
7. 任务可挂接其他项目的 milestone/parent；assignee 无角色/成员校验（FK 异常会变 500）。
8. 项目软删除后 assignee 仍可直接读/评子任务。
9. 实验锁定对 PI 不彻底（PI 可直接编辑/删附件）。
10. 预约 approved 后可被申请人改时间且仍是 approved；状态转换散落 if。
11. 未来预约把 Equipment.status 长期写成 reserved。
12. Borrow 允许过去的 expected_return_time；Maintenance 状态机不完整。
13. due_checker 自定义 utcnow/date.today，绕过统一时间源。
14. 实验编号测试存在永真断言。
15. 周/实验等 mutation schema 接受未知字段（静默忽略）。

| backend/app 文件数 / LOC | 78 / 10649 | +4 / +1899（含新增 Settings 功能 ~600 行与 ruff format 换行展开） |
| backend/tests LOC | 2709 → 3627 | +918（新增 RBAC matrix/Settings/任务规则/查询计数测试） |
| frontend/src 文件数 / LOC | 52 / 7308 | +1 / +293（SettingsView 新页面） |
| pytest | 131 → 160 passed | +29 |
| frontend tests | 6 passed | 6 passed |
| build（dist） | 2799 KB → 2808 KB | +9 KB（Settings 页） |
| GET /dashboard/pi queries | 29 | 29（上一轮已优化，本轮保持） |
| branch coverage | — | 78%（整体），权限/AI 安全/Settings 模块 88–100% |

注：LOC 增量主要来自本轮新增的 Settings 功能（前后端约 675 行）与 ruff format 的换行展开；
旧业务代码的净删除体现在：Planner 移除、权限双实现合并、设备状态同步代码删除、
utcnow/date.today 重复收编、死 schema/helper/HomeView 删除（合计约 380 行），未达 8% 净减目标，
原因已在 FINAL_REPORT.md 说明。
