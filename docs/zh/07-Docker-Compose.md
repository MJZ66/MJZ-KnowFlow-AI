# 07 — Docker Compose 部署

## 开发 / 演示（全栈）

```powershell
cd E:\AI知识平台\knowflow-ai
docker compose up --build -d
```

应启动服务：

```text
postgres
redis
chromadb
backend
celery-worker
frontend（可选，视 compose 配置）
```

## 仅后端链路

```powershell
docker compose up --build -d backend celery-worker
```

适合：本地 `npm run dev` 调试前端。

## 生产 profile

```powershell
docker compose --profile production up --build -d
```

含 Nginx 反向代理（见 `nginx/`）。

## 端口说明

| 服务 | 默认端口 |
|------|----------|
| 前端（Vite / compose） | 3000 |
| 后端 API | 8000 |
| PostgreSQL | 5432 |
| Redis | 6379 |
| ChromaDB（宿主机映射） | 8001 → 容器 8000 |

## 生产要求

- 不使用 `--reload`
- 使用强 `SECRET_KEY`（≥ 32 字符）
- 配置正式 `ALLOWED_ORIGINS`
- 配置 Nginx / Ingress / TLS
- **不要**将 PostgreSQL、Redis、ChromaDB 暴露到公网

## 数据库迁移

```powershell
docker compose exec backend alembic upgrade head
```

索引迁移 `002_performance_indexes` 优化文档与 chunk 查询。

## 相关章节

- [02 — 本地启动](./02-本地启动.md)
- [08 — Kubernetes](./08-Kubernetes.md)
- [10 — 生产安全](./10-生产安全.md)
