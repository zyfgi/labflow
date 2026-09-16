# LabFlow 架构说明

## 总体架构

```
┌──────────┐   :80    ┌─────────┐  /api/  ┌─────────┐  5432  ┌────────────┐
│  浏览器   │ ───────▶ │  nginx  │ ──────▶ │ backend │ ─────▶ │ PostgreSQL │
└──────────┘          │ (边界)  │  其余   │ FastAPI │        │    16      │
                      └────┬────┘ └───────┘  :8000  │        └────────────┘
                           │ / 静态                  │  storage/
                           ▼                        └─▶ 本地文件卷
                    ┌───────────┐
                    │ frontend  │  nginx 静态托管 Vue3 构建产物（SPA fallback）
                    └───────────┘
```

- 四容器编排：`frontend`（构建产物 + 内部 nginx）、`backend`（uvicorn）、`postgres:16-alpine`、`nginx`（唯一公网入口，:80）。
- 后端启动命令自动执行 `alembic upgrade head` 后再启动 uvicorn。
- 本地开发可以不用 Docker：`uvicorn app.main:app --reload` + `npm run dev`（Vite 代理 /api）。

## 后端结构（backend/app）

```
app/
├── main.py            # FastAPI 应用工厂、CORS、/api/health
├── database.py        # SQLAlchemy engine/SessionLocal/Base
├── seed.py            # python -m app.seed（账号 + 调用 seed_data）
├── seed_data.py       # Demo 业务数据（幂等）
├── due_checker.py     # python -m app.due_checker（每日到期检查）
├── core/
│   ├── config.py      # pydantic-settings（环境变量/.env）
│   ├── security.py    # pwdlib(argon2) 密码哈希、PyJWT 签发/校验
│   ├── deps.py        # get_current_user / require_roles / 审计助手
│   └── responses.py   # {data, message} 与分页包装
├── models/            # SQLAlchemy 2.0 模型（enums.py 集中常量）
├── schemas/           # Pydantic v2 请求/响应模型
├── api/v1/            # 路由：auth/users/members/skills/learning_plans/
│                      # weekly_reports/projects/tasks/experiments/
│                      # equipment/dashboard/notifications/search/exports/audit_logs
├── permissions/       # 项目级资源权限（visibility + 成员 + owner + 角色）
├── storage/           # StorageService（文件名清理/白名单/限额/防穿越）
└── services/          # 通知等领域服务
```

## 设计要点

1. **统一响应**：成功 `{data, message}`；分页 `{items,total,page,page_size}`；错误 `{"detail": "..."}`（HTTP 语义码）。
2. **RBAC + 资源权限**：角色（PI/TEACHER/STUDENT/EQUIPMENT_ADMIN/GUEST）+ 项目可见性（private/project_members/lab）+ 项目成员角色 + 资源属主，全部在**后端**强制。
3. **软删除**：projects / tasks / experiments / equipment 用 `deleted_at`；成员/技能/计划等为硬删除（非关键追溯数据）。
4. **可追溯**：全部表带 `created_at/updated_at`；关键操作（登录/建项目/锁实验/审批…）写 `audit_logs`；实验锁定机制保证记录不可篡改（解锁需管理方并记日志）。
5. **通知**：站内 Notification 表，事件在服务层同步写入；定时到期检查由 `due_checker` 完成（V1 不引入 MQ）。
6. **可移植性**：生产 PostgreSQL 16，测试/本地可切 SQLite（`DATABASE_URL`）；模型只用通用类型。
7. **性能**：列表全部分页；Dashboard 单次聚合 API；文件下载流式（FileResponse）不整读内存。

## V2 预留

- 科研成果（Paper/Patent/...）挂在 Project → Experiment → ResearchOutput 链上
- 知识库（KnowledgeDocument/SOP）
- AI 助手：数据已结构化（实体+状态+时间），可直接做查询/问答层，无需改动现有模型
