# KnowFlow AI — Grafana & Prometheus 告警

## 1. Prometheus 告警规则

将规则文件挂载到 Prometheus：

```yaml
# prometheus.yml
rule_files:
  - /etc/prometheus/rules/knowflow-alerts.yml
```

复制本仓库规则：

```bash
cp deploy/grafana/prometheus/knowflow-alerts.yml /path/to/prometheus/rules/
```

## 2. Scrape 配置

```yaml
scrape_configs:
  - job_name: knowflow-backend
    metrics_path: /api/metrics
    scrape_interval: 15s
    static_configs:
      - targets: ["host.docker.internal:8000"]
```

需 `METRICS_ENABLED=true`。

## 3. Grafana 导入告警

1. Grafana → Alerting → Alert rules → Import
2. 选择 Prometheus 数据源
3. 导入 `prometheus/knowflow-alerts.yml` 中同名规则，或通过 Prometheus Ruler 统一管理

## 4. 建议通知渠道

| 严重级别 | 渠道 |
|----------|------|
| critical | 电话 / 钉钉 / 企业微信 |
| warning | Slack / 邮件 |
| info | Grafana 面板 only |

## 5. 可选 Docker Compose（monitoring profile）

```powershell
docker compose --profile monitoring up -d
```

见项目根 `docker-compose.yml` 中 `prometheus` / `grafana` 服务（如已启用）。

## 6. 面板指标

- HTTP QPS / P95 / P99
- `document_process_success_total` vs `failed`
- `celery_task_*`
- RAG cache hit ratio
- `rag_retrieval_total`

## 7. 本地启动监控栈

```powershell
docker compose --profile monitoring up -d prometheus grafana
# Prometheus: http://localhost:9090
# Grafana:    http://localhost:3001  (admin / admin)
```

相关文档：[docs/zh/09-Prometheus.md](../../docs/zh/09-Prometheus.md)
