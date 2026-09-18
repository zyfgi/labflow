# 内网 HTTPS 部署（Let's Encrypt DNS-01 + Nginx TLS）

LabFlow 是内网科研协同系统。推荐用**真实域名 + Let's Encrypt DNS-01** 签发免费证书，
Nginx 做 TLS 终结；PostgreSQL 与 FastAPI 直接端口**不对内网以外暴露**。

## 架构

```
微信/手机/PC ──HTTPS 443──> Nginx (TLS 终结, 静态前端 + /api 反代)
                                │
                                ├── frontend dist (静态文件)
                                └── uvicorn 127.0.0.1:8000 (仅本机)
                                     └── PostgreSQL 127.0.0.1:5432 (仅本机)
```

前提：你拥有一个域名（例如 `lab.example.edu`），并把它的 A 记录指向内网服务器 IP
（split DNS：内网解析到内网 IP，公网可指向内网或不开 443 —— 证书签发用 DNS 验证，
不需要公网可达）。

## 1. DNS-01 签发证书（certbot）

```bash
# 以 Cloudflare 为例（其他 DNS 插件见 certbot 文档）
sudo apt install certbot python3-certbot-dns-cloudflare
cat > ~/.secrets/cloudflare.ini <<'EOF'
dns_cloudflare_api_token = YOUR_DNS_TOKEN
EOF
chmod 600 ~/.secrets/cloudflare.ini

sudo certbot certonly \
  --dns-cloudflare \
  --dns-cloudflare-credentials ~/.secrets/cloudflare.ini \
  -d lab.example.edu
```

自动续期（certbot 装好后自带 timer，确认即可）：

```bash
sudo certbot renew --dry-run
```

## 2. Nginx 配置

`nginx/nginx-labflow.conf` 是完整示例，要点：

- 证书路径指向 `/etc/letsencrypt/live/lab.example.edu/`；
- HTTP 80 仅做 301 跳转 HTTPS；
- `location /` 指向前端构建产物（`frontend/dist`）；
- `location /api/` 反代 `http://127.0.0.1:8000`；
- `/q/{token}` 路径由前端路由处理（二维码落地页），无需特殊配置；
- 手机 Web / 微信小程序共用同一域名。

```bash
sudo cp nginx/nginx-labflow.conf /etc/nginx/sites-available/labflow
sudo ln -s /etc/nginx/sites-available/labflow /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

## 3. 后端只监听本机

```bash
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
```

`.env` 关键项（生产）：

```
LABFLOW_ENV=production
LABFLOW_DEBUG=false
LABFLOW_SECRET_KEY=<随机 64+ 字符>
DATABASE_URL=postgresql://labflow:<密码>@127.0.0.1:5432/labflow
LABFLOW_CORS_ORIGINS=https://lab.example.edu
```

PostgreSQL 监听 `127.0.0.1`（`postgresql.conf` 的 `listen_addresses`），防火墙
**不要**放行 5432 与 8000 —— 只有 80/443 对外。

## 4. 定时任务（超期检查）

```cron
30 8 * * *  cd /opt/labflow/backend && .venv/bin/python -m app.due_checker
```

## 5. 微信小程序

- 「系统设置 → 基础设置」打开「微信小程序入口」，`PUBLIC_BASE_URL` 填
  `https://lab.example.edu`；
- 小程序 `app.js` 的 `apiBase` 改为 `https://lab.example.edu/api/v1`；
- request 合法域名在小程序后台配置为该域名（须 HTTPS）。

## 安全校验清单

- [ ] `curl http://lab.example.edu` 301 到 https
- [ ] `curl -I https://lab.example.edu/api/health` 200
- [ ] 服务器外网扫描 5432/8000 不通
- [ ] `certbot renew --dry-run` 通过
- [ ] 系统设置里 `SECRET_KEY` 显示 configured，DATABASE_URL 密码已掩码
