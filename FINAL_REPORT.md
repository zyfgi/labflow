# FINAL_REPORT — 轻流程协同轮（LabFlow_下一轮_Agent执行手册_轻流程协同版）

> 基线 `0da8ce8` → 本轮提交。一次性无人值守执行。上一轮报告已被本文件覆盖（Git 保留历史）。

本轮核心原则：**LabFlow 是科研协同记录系统，不是 OA 审批系统。**
所有不必要的审批/审核/退回替换为：直接执行 → 通知相关人员 → 完整留痕。
未引入工作流引擎 / BPM / 审批引擎 / Redis / MQ / 微服务。

## 1. 删除了哪些审批流程

| 旧流程 | 新流程 | 代码处理 |
| --- | --- | --- |
| 周报 draft→submitted→reviewed/returned，submit/review/return 端点 | draft→published；发布后可继续改，评论取代审核 | 端点直接删除（404）；`submitted_at` 迁移改名 `published_at`；新增 `WeeklyReportComment` |
| 预约 pending→approved/rejected，approve/reject 端点 | 无冲突即 `reserved`，冲突 409，取消即时 | 端点直接删除（404）；`approved_by/approved_at` 保留为 legacy unused（nullable，不再写入） |
| 借用人工批准（旧字段遗留） | 可用即借出；归还即时；**延期**=PATCH `expected_return_time` + 通知管理员 | legacy `approved_by` 列保留未用 |
| 任务 `review` 状态（强制复核节点） | 状态收敛为 todo/in_progress/blocked/done/cancelled；review→done 无需他人批准 | 旧数据迁移至 `in_progress` |
| 项目成员需接受确认 | 添加立即生效，被添加人收到通知，无需确认 | 文案/文档澄清（本就无确认端点） |
| 学生不能建项目 | 运行时设置 `STUDENT_CAN_CREATE_PROJECT`（默认 **true**） | PI 可在设置中心关闭 |

**审批相关代码删除行数（净）**：后端约 **-394** 行（weekly_reports 审核链 3 端点、equipment approve/reject 2 端点、dashboard 待审批卡、due_checker 旧状态），测试删除旧审批用例约 **-260** 行。
**审批相关测试删除/重写数量**：删除 9 个旧审批用例（approve/reject 通知、审核/退回流、改期回退待审批等），重写为 15 个设备 + 12 个周报轻流程契约用例，新增 8 个核心用例（`test_light_process.py`）。

## 2. 新的通知事件（24 个）

`app/services/notifications.py::NOTIFICATION_EVENTS`（净增 **13**）：

- 项目/任务：`project_created` `project_member_added` `task_assigned` `task_reassigned` `task_due_changed` `task_completed` `task_due_soon` `task_overdue`
- 周报：`weekly_report_published` `weekly_report_updated` `weekly_report_commented`
- 实验：`experiment_created` `experiment_updated` `experiment_locked` `experiment_unlocked`
- 设备：`equipment_booked` `equipment_booking_cancelled` `equipment_borrowed` `equipment_returned` `equipment_overdue` `equipment_fault` `maintenance_updated`
- 微信：`wechat_bound` `wechat_unbound`

只发给真正相关人（assignee、设备管理员/负责人、受影响预约人、报告人、PI）；`notify()` 统一去重并排除操作者本人；禁止全实验室广播。通知只有已读/未读，无确认/签收。`NOTIFICATION_ENABLED=false` 时静默（动作照常、审计照写）。

## 3. Audit 覆盖的 mutation 数

**31** 个动作类型写 `audit_logs`：create/update/delete（project/task/milestone/weekly_report/experiment/equipment）、publish_weekly_report、comment_weekly_report、create/cancel_booking、borrow/extend_borrow/return_equipment、report_fault、update_maintenance、lock/unlock_experiment、generate/regenerate_qr、create_wechat_binding_code、bind/unbind_wechat、update_runtime_settings 等。不记录任何密码/密钥/绑定码明文。

## 4. 权限变化

- **read collaboration / write ownership**：已发布周报全实验室（PI/TEACHER/STUDENT）可读，草稿仅本人；学生可看其他成员科研进度（列表/AI 检索同步放开；侧信道安全：学生检索他人只能命中 published）。
- EQUIPMENT_ADMIN/GUEST 仍被挡在科研域之外；AI 三层泄漏测试（SECRET_PROJECT_B_TOKEN_9F83A）与全部安全测试保持通过。
- 新增：学生建项目受运行时开关控制；微信首次绑定需 PI 一次性绑定码（禁止自动注册）。

## 5. 多端适配

- **手机 Web**：MainLayout <768px 侧栏变抽屉、≥992 桌面完整布局；Dashboard/周报/设备/详情页 `:xs/:md` 断点；移动首页 = 通知/最近动态/需关注（无待审批）。
- **微信小程序**（`miniprogram/`，原生，约 1,100 行）：首页（通知+动态+需关注）/成员/科研（项目/任务/实验/周报：发布+评论）/扫码（预约·借用·归还·故障上报）/AI/我的 + 登录 + 绑定 + 通知中心 + 设备详情。无审批收件箱。
- PC：所有角色功能完整（学生可建项目、管理有权限的任务、发布周报）。

## 6. QR

`POST /equipment/{id}/qr`（生成）、`?regenerate=true`（重生成→旧标签立即失效）；详情页显示/下载 PNG；`GET /qr/{token}` 服务端解析；Web `/q/{token}` 落地页直达设备。标签 URL = `PUBLIC_BASE_URL/q/{token}`（设置中心可配，留空为站内路径）。**二维码不是凭证**：扫码后仍走正常认证与 RBAC。

## 7. WeChat

`app/api/v1/wechat.py`：`POST /wechat/session`（code2Session，已绑定直接发 JWT）、`POST /wechat/bind`（账号密码 + PI 一次性绑定码）、`DELETE /wechat/bind`（自助解绑，确认后立即生效）、绑定码签发/列表（PI only，30 分钟、一次性、用后即焚、审计不留明文）。`WECHAT_APPID/WECHAT_SECRET` 仅存后端 `.env`；未配置时开发环境支持 `mock:<openid>`。入口受 `WECHAT_MINIPROGRAM_ENABLED` 控制（默认关）。

## 8. HTTPS

`docs/intranet-https.md` + `nginx/nginx-labflow.conf`：真实域名 + Let's Encrypt **DNS-01**（内网也能签）+ Nginx TLS 终结；HTTP→HTTPS 301；PostgreSQL/uvicorn 仅监听 127.0.0.1，防火墙不放行 5432/8000；HSTS 等安全头；certbot 自动续期校验清单。

## 9. 测试

```
backend:  174 passed · ruff format/check (F401,F811,F841) 全过
frontend: typecheck 0 errors · vitest 6 passed · vite build ✓
DB:       全新库 alembic upgrade head → 26 表；存量库迁移验证：
          submitted/reviewed→published、returned→draft、pending/approved→reserved、
          rejected→cancelled、task review→in_progress、submitted_at→published_at 全部正确
```

## 10. LOC before / after

| 范围 | before (0da8ce8) | after | Δ |
| --- | --- | --- | --- |
| backend/app | 10,649 | 11,367 | +718（新增 wechat 289 + QR 90 + 评论/通知中心 ~120；审批净删 -394 被新功能抵消） |
| frontend/src | 7,410 | 7,766 | +356（QR 落地页/绑定码管理/评论；审批 UI 净删 -216） |
| miniprogram | 0 | 1,097 | +1,097（全新端） |

审批路径本身显著缩减：周报审核 3 端点→0、预约审批 2 端点→0、Dashboard 待审批卡 2→0、任务 review 状态移除；新增行全部来自本轮要求的微信/QR/评论/多端能力。

## 遗留说明（手册 §72 legacy fields）

`equipment_bookings.approved_by/approved_at`、`equipment_borrows.approved_by`、
`weekly_reports.reviewer_id/reviewed_at/review_comment` 为 **legacy unused**：
nullable 保留、业务零引用、模型处有注释标记；下一轮可出独立迁移清理。

## 最终验收指标对照（手册 §75）

- [x] 周报无强制审核 / 预约无审批 / 借用无审批 / 项目成员加入无确认 / 任务完成无审批 / 故障上报立即生效
- [x] 周报·任务·项目·预约·借还·故障·维修 全部有通知
- [x] 所有重要 mutation 写 AuditLog
- [x] 学生可查看其他成员科研进度，不能改无权限数据（安全测试全绿）
- [x] teacher/student × PC / 手机 Web / 微信小程序 三端一致
- [x] QR 生成/绑定/下载/重生成失效/扫码解析
- [x] 内网 HTTPS（DNS-01 + Nginx）方案与配置交付
