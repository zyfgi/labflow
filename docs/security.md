# 安全说明

本文汇总 LabFlow 的安全设计与本轮（AI 阶段）新增的安全整改。

## 认证与凭据

- 密码仅存 argon2 哈希（pwdlib）；登录失败统一文案，不泄露用户名是否存在。
- JWT 有效期可配置（默认 24h）；`SECRET_KEY` 生产启动校验：禁止开发默认值、长度 ≥ 32。
- API Key（AI 提供商）仅存在于后端环境变量；`/ai/status` 只返回 `api_key: configured`，永不回显。

## 生产配置 Fail-Fast（新增）

`ENV=production` 启动时强制校验，任一不满足即拒绝启动并给出明确错误：

```text
DEBUG 必须 false
SECRET_KEY 非默认值且长度 ≥ 32
DATABASE_URL 不得为 SQLite
AI_ENABLED=true 时必须配置 AI_BASE_URL / AI_API_KEY / AI_MODEL
```

## Seed 与生产隔离（新增）

- `ENV=production` 时 `python -m app.seed` 默认拒绝执行（`ALLOW_DEMO_SEED=true` 可显式覆盖）。
- 生产初始化管理员使用独立命令：`python -m app.cli create-admin`
  （`ADMIN_USERNAME/ADMIN_EMAIL/ADMIN_NAME/ADMIN_PASSWORD` 环境变量或交互输入，不使用固定 demo 密码）。

## 权限模型

- RBAC（五角色）+ 项目级资源权限（visibility + 成员 + owner），全部后端强制。
- **查询级权限 Scope**（本轮新增）：`visible_project_ids_subquery` /
  `apply_project_read_scope` 统一约束 Project/Task/Experiment 列表、Search、Export、AI Retrieval，
  权限条件在 SQL 内生效，杜绝"先取数再过滤"。
- 设备管理员（EQUIPMENT_ADMIN）本轮收紧：只能访问设备域（台账/预约/借用/维修）；
  成员档案、学习计划、技能、周报、科研进度一律 403；预约人/借用人仅显示 user_id+姓名。

## AI 安全边界

- AI 为只读助手；LLM 不接触数据库、不持有独立权限。
- **AI 可见数据 = 当前用户普通 API 可见数据**，过滤在检索 SQL 内完成。
- 数据最小化白名单字段；禁止发送 password_hash/email/phone/学号/采购价/审计/API Key/JWT。
- Prompt Injection 防护：System Prompt 声明检索记录为不可信数据；`<labflow_source>` 边界包裹。
- 防侧信道：无权限数据与不存在数据响应一致（"没有找到足够信息"）。
- 限流：每用户 10 次/分钟、100 次/天（可配置，应用内实现，无 Redis 依赖）。
- 审计：`ai_chat / ai_retrieve / ai_provider_error` 写 AuditLog；`AIRequestLog`
  记录 model/tokens/latency/status；默认不记录问题原文（`AI_AUDIT_STORE_QUERY=false`）。
- 错误脱敏：对外仅返回错误码与友好文案，不返回 stack trace / provider 原始响应 / key。

## 文件与基础设施

- 上传：文件名清理 + UUID 前缀 + 扩展名白名单 + 100MB 限额（可配）+ 路径穿越防护。
- 下载：仅经鉴权 API（FileResponse 流式），静态目录不暴露上传件。
- 数据库仅绑定 127.0.0.1（compose）；CORS 白名单可配置；生产 `DEBUG=false`。
- `.env` 不入库；仓库无真实密钥（CI 可用 `git grep` 校验占位符）。

## 关键安全测试

```text
tests/test_p0_hardening.py      设备管理员隔离 / production fail-fast / seed 守卫
tests/test_ai_permissions.py    SECRET_PROJECT_B_TOKEN：search / retrieve / LLM payload 三层 0 泄漏
tests/test_ai_injection.py      注入指令只能作为 source 证据、planner 不携带业务数据
tests/test_ai_chat.py           会话所有权（PI 也不可读他人对话）/ 错误脱敏 / 限流
```
