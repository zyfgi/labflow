# API 概览

- 统一前缀：`/api/v1`；交互式文档：`/api/docs`（Swagger）
- 认证：`Authorization: Bearer <JWT>`；登录签发，默认 24h 有效
- 成功响应：`{"data": ..., "message": "success"}`；分页：`{"items": [...], "total": n, "page": 1, "page_size": 20}`；错误：`{"detail": "..."}`

## 认证 Auth
```
POST /auth/login                  {username, password} -> {access_token, must_change_password, user}
POST /auth/logout                 登出（审计记录）
GET  /auth/me                     当前用户
POST /auth/change-password        {old_password, new_password}
```

## 用户 Users（PI 管理；教师可读）
```
GET/POST /users        GET/PATCH /users/{id}      GET /users/options（下拉）
PATCH /users/{id}      支持 role/status/重置密码；角色变更写审计
```

## 成员 / 技能 / 学习计划
```
GET  /members                       POST /members       GET /members/me
GET  /members/{id}                  PATCH /members/{id} GET /members/{id}/overview
GET/POST /skills                    GET/PUT /members/{id}/skills
GET/POST /learning-plans            PATCH/DELETE /learning-plans/{id}
```

## 周报
```
GET/POST /weekly-reports            GET/PATCH /weekly-reports/{id}
POST /weekly-reports/{id}/submit|review|return
GET  /weekly-reports/me/current
```
状态机：`draft → submitted → reviewed`；`submitted → returned →（修改）→ submitted`

## 项目 / 里程碑 / 任务
```
GET/POST /projects                  GET/PATCH/DELETE /projects/{id}
GET/POST /projects/{id}/members     DELETE /projects/{id}/members/{user_id}
GET/POST /projects/{id}/milestones  PATCH/DELETE /milestones/{id}
GET/POST /tasks                     GET/PATCH/DELETE /tasks/{id}
POST /tasks/{id}/status             GET/POST /tasks/{id}/comments
```
项目可见性：`private`（负责人+PI）/ `project_members`（成员）/ `lab`（全实验室）；学生只读/编辑自己的任务状态与进度。

## 实验记录
```
GET/POST /experiments               GET/PATCH/DELETE /experiments/{id}
POST /experiments/{id}/lock|unlock
POST /experiments/{id}/attachments            （multipart，白名单 ext，100MB 限额）
DELETE /experiment-attachments/{id}
GET  /experiment-attachments/{id}/download    （鉴权流式下载）
```
实验编号自动生成：`EXP-YYYYMMDD-XXXX`；锁定后普通成员不可修改/传附件。

## 设备
```
GET/POST /equipment                 GET/PATCH/DELETE /equipment/{id}
GET/POST /equipment-bookings        PATCH /equipment-bookings/{id}
POST /equipment-bookings/{id}/approve|reject|cancel
GET/POST /equipment-borrows         POST /equipment-borrows/{id}/return
GET/POST /equipment-maintenance     PATCH /equipment-maintenance/{id}
```
预约冲突（同设备 pending/approved 重叠）后端 409；借出后设备状态 `borrowed`，归还恢复。

## Dashboard / 通知 / 搜索 / 导出 / 日志
```
GET /dashboard/pi                   GET /dashboard/student
GET /notifications                  POST /notifications/{id}/read   POST /notifications/read-all
GET /search?q=                      GET /exports/{members|weekly-reports|tasks|equipment|equipment-bookings}?format=csv|xlsx
GET /audit-logs                     （仅 PI）
```

## 其它
```
GET /api/health                     存活检查（compose healthcheck 使用）
```
