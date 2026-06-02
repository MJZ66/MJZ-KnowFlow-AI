# KnowFlow AI — 生产部署指南

完整开发与验收流程见：[docs/zh/README.md](../docs/zh/README.md)（分章索引）· [docs/DEPLOYMENT_AND_DEVELOPMENT.md](../docs/DEPLOYMENT_AND_DEVELOPMENT.md)（汇总）

## 环境分层

| 环境 | `APP_ENV` | `METRICS_ENABLED` | `RAG_CACHE_ENABLED` | `SECRET_KEY` |
|------|-----------|-------------------|---------------------|--------------|
| **dev** | `development` | `true`（可选） | `false` | 可默认，启动时警告 |
| **staging** | `development` 或 `production` | `true` | `true` | 建议 ≥ 32 字符 |
| **prod** | `production` | `true` | `true` | **必须** ≥ 32 字符，否则进程拒绝启动 |

模板文件（勿提交真实密钥）：

- `.env.example` / `.env.development.example` — 本地 Docker Compose 开发
- `.env.staging.example` — 预发（Hybrid / Reranker / RAG 缓存）
- `.env.production.example` — 生产（CORS、连接池、Celery）

### 关键环境变量

| 变量 | 说明 |
|------|------|
| `ALLOWED_ORIGINS` | 逗号分隔前端域名，供 CORS |
| `TASK_BACKEND` | `celery`（生产）或 `background`（单机调试） |
| `HYBRID_SEARCH_ENABLED` | 混合检索 |
| `RERANKER_ENABLED` | 重排序 |
| `RAG_CACHE_ENABLED` | Redis RAG 结果缓存 |
| `METRICS_ENABLED` | `false` 时 `/api/metrics` 返回 404 |
| `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` | SQLAlchemy 连接池 |

## Docker Compose（单机 / 小规模）

```powershell
cd knowflow-ai
docker compose up --build -d backend celery-worker
```

健康检查：

- Liveness: `GET /api/health/live`
- Readiness: `GET /api/health/ready`（PostgreSQL、Redis、ChromaDB）
- Celery: Redis key `knowflow:celery:worker:heartbeat`

资源限制见 `docker-compose.yml` 中 `deploy.resources`。

## Kubernetes 部署顺序

```bash
kubectl apply -f deploy/k8s/namespace.yaml
kubectl apply -f deploy/k8s/configmap.yaml
# 从示例复制并填写真实值（不要提交到 git）：
cp deploy/k8s/secret.yaml.example deploy/k8s/secret.yaml
# 从示例复制（勿提交真实 secret.yaml）：
cp deploy/k8s/secret.yaml.example deploy/k8s/secret.yaml
# 编辑后：
kubectl apply -f deploy/k8s/secret.yaml
kubectl apply -f deploy/k8s/postgres-statefulset.yaml
kubectl apply -f deploy/k8s/redis-deployment.yaml
kubectl apply -f deploy/k8s/chromadb-deployment.yaml
kubectl apply -f deploy/k8s/backend-deployment.yaml
kubectl apply -f deploy/k8s/celery-deployment.yaml
# 可选 Ingress（需先部署前端 Service）：
kubectl apply -f deploy/k8s/ingress.yaml.example
```

### Secret 示例

见 `deploy/k8s/secret.yaml.example`。生产至少设置：

- `SECRET_KEY` — 随机 ≥ 32 字符
- `LLM_API_KEY` / `DEEPSEEK_API_KEY` — 按所用模型填写

ConfigMap（非敏感）见 `deploy/k8s/configmap.yaml`，含 `METRICS_ENABLED`、`RAG_CACHE_ENABLED` 等。

### Backend / Celery 探针与资源

`backend-deployment.yaml` 已配置：

- `resources.requests/limits`（CPU / 内存）
- `livenessProbe` → `/api/health/live`
- `readinessProbe` → `/api/health/ready`

`celery-deployment.yaml` 已配置资源限制；worker 存活依赖 Redis heartbeat（readiness 可通过自定义脚本检查该 key）。

### Ingress / TLS

参考 `deploy/k8s/ingress.yaml.example`：

- TLS 证书可用 cert-manager + Let's Encrypt
- `proxy-body-size` 需 ≥ 上传限制（默认 30MB）
- SSE 问答建议 `proxy-read-timeout` ≥ 300s

## Prometheus 监控

### 抓取端点

```
GET /api/metrics
Content-Type: text/plain; version=0.0.4; charset=utf-8
```

需 `METRICS_ENABLED=true`（ConfigMap 默认已开启）。

### 主要指标

| 指标 | 含义 |
|------|------|
| `http_requests_total` | HTTP 请求计数（method, endpoint, status） |
| `http_request_duration_seconds` | 请求耗时直方图 |
| `rag_cache_hit_total` / `rag_cache_miss_total` | RAG 缓存命中/未命中 |
| `rag_retrieval_total` | 实际检索次数 |
| `document_process_success_total` / `document_process_failed_total` | 文档处理成败 |
| `document_process_duration_seconds` | 文档处理耗时 |
| `celery_task_success_total` / `celery_task_failed_total` | Celery 任务成败 |

### scrape 配置示例

```yaml
scrape_configs:
  - job_name: knowflow-backend
    metrics_path: /api/metrics
    static_configs:
      - targets: ['knowflow-backend.knowflow.svc.cluster.local:8000']
    scrape_interval: 15s
```

Grafana：导入 FastAPI / Prometheus 通用面板，或按上述指标自建 RAG / Celery 面板。

## 数据库迁移

```bash
docker compose exec backend alembic upgrade head
```

索引迁移 `002_performance_indexes` 优化文档与 chunk 查询。

## 日志建议

- 容器 stdout → Fluent Bit / Loki / ELK
- 标签：`service=knowflow`, `component=backend|celery|rag`
- RAG 日志：`rag_cache_hit`, `rag_cache_miss`, `rag_cache_invalidated`, `raw_retrieved_count`

## 验收命令

```powershell
cd knowflow-ai
docker compose up --build -d backend celery-worker

cd backend
python scripts/e2e_acceptance.py
docker compose exec backend pytest tests/ -v
python scripts/retrieval_quality_check.py

cd ..\frontend
npm run build
npm run test:run
# 需另开终端: npm run dev
npm run e2e
```
