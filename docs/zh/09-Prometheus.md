# 09 — Prometheus 监控

## Endpoint

```text
GET /api/metrics
Content-Type: text/plain; version=0.0.4; charset=utf-8
```

需 `METRICS_ENABLED=true`（默认开启）；关闭时返回 **404**。

本地验证：

```powershell
curl http://localhost:8000/api/metrics
```

## 当前指标

| 指标 | 含义 |
|------|------|
| `http_requests_total` | HTTP 请求计数（method, endpoint, status） |
| `http_request_duration_seconds` | 请求耗时直方图 |
| `rag_cache_hit_total` | RAG 缓存命中 |
| `rag_cache_miss_total` | RAG 缓存未命中 |
| `rag_retrieval_total` | 实际检索次数 |
| `document_process_success_total` | 文档处理成功 |
| `document_process_failed_total` | 文档处理失败 |
| `document_process_duration_seconds` | 文档处理耗时 |
| `celery_task_success_total` | Celery 任务成功 |
| `celery_task_failed_total` | Celery 任务失败 |

实现位置：`backend/app/core/metrics.py`，在 RAG、文档处理、Celery 任务中打点。

## Prometheus scrape 示例

```yaml
scrape_configs:
  - job_name: knowflow-backend
    metrics_path: /api/metrics
    scrape_interval: 15s
    static_configs:
      - targets:
          - knowflow-backend.knowflow.svc.cluster.local:8000
```

Docker Compose 单机：

```yaml
static_configs:
  - targets: ["host.docker.internal:8000"]
```

## 建议 Grafana 面板

- HTTP 请求量（按 endpoint）
- HTTP P95 / P99 延迟
- RAG cache hit / miss 比率
- `rag_retrieval_total` 趋势
- 文档处理成功 / 失败数
- Celery 任务成功 / 失败数

## 日志配合

容器 stdout 关键字（便于 Loki / ELK 过滤）：

```text
rag_cache_hit
rag_cache_miss
rag_cache_invalidated
raw_retrieved_count
```

## 相关章节

- [06 — 环境变量](./06-环境变量.md)
- [08 — Kubernetes](./08-Kubernetes.md)
