# 部署说明

## 生产部署（Docker Compose，推荐）

```bash
git clone <repo>
cd labflow
cp .env.example .env

# 编辑 .env，务必修改：
#   LABFLOW_SECRET_KEY（python -c "import secrets; print(secrets.token_urlsafe(48))"）
#   POSTGRES_PASSWORD / DATABASE_URL 中的密码
vim .env

docker compose up -d --build
# backend 容器启动时自动执行 alembic upgrade head
# 初始化 demo 数据（可选，生产请跳过或改密）：
docker compose exec backend python -m app.seed
```

访问：

- 应用：`http://<服务器>:80`
- API 文档：`http://<服务器>/api/docs`
- 健康检查：`http://<服务器>/api/health`

### 每日定时任务（到期检查）

```bash
crontab -e
# 每天 08:00 执行到期检查（任务截止提醒/逾期/借用逾期/预约归档）
0 8 * * * cd /path/to/labflow && docker compose exec -T backend python -m app.due_checker
```

### 日志与运维

```bash
docker compose ps                 # 四容器状态（postgres/backend 有 healthcheck）
docker compose logs -f backend    # 后端日志
docker compose restart backend
docker compose down               # 数据保留（pgdata 卷）
```

## 升级

```bash
git pull
docker compose build
docker compose up -d
# 迁移随 backend 启动自动执行；也可手动：
docker compose exec backend alembic upgrade head
```

## 生产安全清单

- [x] `.env` 不入库（.gitignore 已排除），所有默认密码/密钥为占位符
- [x] `LABFLOW_DEBUG=false`（compose 已设置）；`LABFLOW_ENV=production`
- [x] PostgreSQL 仅绑定 `127.0.0.1:5432`，不对公网暴露；跨容器走内部网络
- [x] CORS 通过 `CORS_ORIGINS` 白名单配置
- [x] 上传文件不在 nginx 静态目录中，一律走鉴权 API 下载
- [x] nginx `client_max_body_size 200m` 与后端 `UPLOAD_MAX_MB` 联动
- [ ] 建议在生产前为 nginx 配置 TLS（终止在边界层）

## 非 Docker 部署

需求：Python 3.12+、Node 20+、PostgreSQL 16。

```bash
# 后端
cd backend && python -m venv .venv
.venv/bin/pip install -r requirements.txt
export DATABASE_URL=postgresql+psycopg2://user:pass@127.0.0.1:5432/labflow
export LABFLOW_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(48))")
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000   # 用 systemd/supervisor 托管

# 前端
cd frontend && npm ci && npm run build
# 将 dist/ 交给任意静态服务器，并把 /api 反代到 8000（参考 nginx/default.conf）
```

Windows 本地开发注意事项：若使用嵌入式 PostgreSQL（pgserver 二进制），initdb 需要纯 ASCII 路径与 `--locale=C`，参见 `scripts/dev_pg.py` 注释。
