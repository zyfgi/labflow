# Retrieval 架构

## 代码结构

```text
backend/app/services/retrieval/
├── __init__.py        # 导出公共 API
├── types.py           # RetrievalHit / RetrievalPlan / SourceType / Intent / TimePreset
├── access.py          # 查询级权限 Scope（唯一权限真源）
├── common.py          # 时间预设解析 / 截断工具
├── entity_resolver.py # Layer A：成员/项目/设备/实验编号实体解析
├── intent_parser.py   # Layer B：规则意图识别 + 关键词提取（纯函数，无 DB/LLM）
├── engine.py          # retrieve() 统一入口：分派→合并→排序→截断
├── projects.py  tasks.py  experiments.py  weekly_reports.py
├── equipment.py       # 设备 / 维修 / 预约
└── members.py         # 成员 / 学习计划
```

## 统一权限 Scope（access.py）

```python
visible_project_ids_subquery(user)   # SQL 子查询：用户可读项目 id 集合
apply_project_read_scope(stmt, user, project_column)  # 约束任意 stmt 的项目外键
scoped_tasks_stmt(user)              # 任务 = 可读项目 ∪ 本人负责
```

规则：PI 全量；GUEST 无；其他人 = owner ∪ 在册成员（left_at 为空）∪ `visibility=lab`。
以下模块**共享同一 Scope**，不允许各自复制权限条件：

```text
Project 列表 / Task 列表 / Experiment 列表 / Search / AI Retrieval / Export
```

设备管理员的成员数据隔离：`TEACHING_STAFF_ROLES = (PI, TEACHER)`；
成员档案/学习计划/技能/周报/检索成员目录对 EQUIPMENT_ADMIN 关闭（预约人/借用人仅展示 user_id+姓名）。

## 四层检索策略

| 层 | 职责 | 实现 |
| --- | --- | --- |
| A 实体解析 | 从问题中定位具体实体 | 数据库实体名回查问题文本（成员名/项目名/项目 code/设备名/资产号/EXP 编号正则） |
| B 意图识别 | 决定查哪些 source | 规则表（逾期→task、维修→equipment+maintenance、周报→weekly_report…）+ 时间预设（今天/本周/最近30天…）+ mine_only（"我的"） |
| C 关键词检索 | 非实体内容匹配 | ILIKE 子串（CJK 2-gram）+ 字段权重（编号+6/标题+4/结论+3/方法+2）+ 时间权重 |
| D 结构化直查 | 明确问题直接 SQL | "我的逾期任务"→assignee+due_date<today+status 过滤；"六维力传感器状态"→实体直查 |

**召回兜底**：关键词过窄导致 0 命中时，仅对"开放性自然语言问题"回退为
Scope 内按时间排序的宽松召回；实体指向型查询与精确 token 查询**不回退**
（避免侧信道，满足 §43/§44 的 0 命中要求）。日期敏感源（实验/周报/项目）回退时保留时间过滤。

## 统一结果结构

```python
@dataclass
class RetrievalHit:
    source_type: str      # project/task/experiment/weekly_report/equipment/maintenance/booking/member/learning_plan
    source_id: int
    title: str
    excerpt: str
    score: float
    url: str | None       # 后端生成的站内路由
    project_id: int | None
    occurred_at: datetime | date | None
    metadata: dict        # 含白名单 context 字段（供 Context Builder 渲染）
```

## 与 Search / AI 的关系

```text
GET /api/v1/search        → engine（面向 UI，每类 ≤5 条）
POST /api/v1/ai/retrieve  → engine（调试，返回 plan + hits + 耗时）
POST /api/v1/ai/chat      → engine → context builder → LLM
```

三者权限行为完全一致——测试断言 /search 看不到的数据，/ai/retrieve 与
LLM context 同样看不到（见 tests/test_ai_permissions.py）。

## 性能

- 权限全部下推 SQL（IN 子查询 + 索引），无 Python 逐条 can_read，无 N+1。
- 每源 LIMIT 有界（≤8），总量 ≤ AI_MAX_RETRIEVAL_HITS（默认 16）。
- 典型检索耗时目标 < 300ms（实验室规模数据）。
- 索引覆盖：projects.name/code、tasks.project_id/assignee_id/status/due_date、
  experiments.project_id/experiment_no/experiment_date、weekly_reports.member_id/week_start、
  equipment.asset_no/name（建表迁移已含）。
