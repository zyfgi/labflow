# 备份与恢复

## 备份内容

1. **PostgreSQL 数据库**（全部业务数据）
2. **storage/ 目录**（实验附件等上传文件 —— 文件本体不存数据库，必须同时备份）

## 手动备份

```bash
./scripts/backup.sh              # 输出到 ./backups/
./scripts/backup.sh /data/backup # 指定目录
```

等价手动操作：

```bash
docker compose exec -T postgres pg_dump -U labflow labflow > backup.sql
tar -czf storage.tar.gz storage/
```

## 恢复

```bash
./scripts/restore.sh backups/labflow_db_YYYYMMDD_HHMMSS.sql backups/labflow_storage_YYYYMMDD_HHMMSS.tar.gz
```

等价手动操作：

```bash
docker compose exec -T postgres psql -U labflow labflow < backup.sql
tar -xzf storage.tar.gz -C .
docker compose restart backend
```

## 定时备份（建议）

```bash
crontab -e
# 每天 02:00 备份，保留最近 7 天
0 2 * * * cd /path/to/labflow && ./scripts/backup.sh ./backups && find ./backups -mtime +7 -delete
```

## 注意事项

- 恢复数据库前建议停止 backend：`docker compose stop backend`
- `storage/` 与数据库必须**成对**恢复，否则附件元数据与文件不一致
- 完整恢复后访问 `/api/health` 验证，并用 `alembic current` 确认版本一致
- pg_dump 版本应 ≥ 服务器版本（compose 内置客户端与 postgres:16 匹配）
