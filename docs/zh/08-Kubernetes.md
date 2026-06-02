# 08 — Kubernetes 部署

清单目录：`deploy/k8s/`

详细说明另见：[deploy/README.md](../../deploy/README.md)

## 清单文件

| 文件 | 说明 |
|------|------|
| `namespace.yaml` | 命名空间 `knowflow` |
| `configmap.yaml` | 非敏感配置（含 `METRICS_ENABLED` 等） |
| `secret.yaml.example` | Secret 示例，复制后编辑 |
| `postgres-statefulset.yaml` | PostgreSQL StatefulSet |
| `redis-deployment.yaml` | Redis |
| `chromadb-deployment.yaml` | ChromaDB |
| `backend-deployment.yaml` | API + Service + probes + resources |
| `celery-deployment.yaml` | Celery worker + liveness |
| `ingress.yaml.example` | Ingress / TLS 示例 |

## 推荐 apply 顺序

```bash
kubectl apply -f deploy/k8s/namespace.yaml
kubectl apply -f deploy/k8s/configmap.yaml
cp deploy/k8s/secret.yaml.example deploy/k8s/secret.yaml
# 编辑 secret.yaml 填入真实密钥（勿提交 git）
kubectl apply -f deploy/k8s/secret.yaml
kubectl apply -f deploy/k8s/postgres-statefulset.yaml
kubectl apply -f deploy/k8s/redis-deployment.yaml
kubectl apply -f deploy/k8s/chromadb-deployment.yaml
kubectl apply -f deploy/k8s/backend-deployment.yaml
kubectl apply -f deploy/k8s/celery-deployment.yaml
# 按需：
kubectl apply -f deploy/k8s/ingress.yaml.example
```

## Secret 示例

不要提交真实 Secret 到仓库。

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: knowflow-secret
  namespace: knowflow
type: Opaque
stringData:
  SECRET_KEY: "replace-with-strong-secret-min-32-chars"
  LLM_API_KEY: "replace-with-key"
  DEEPSEEK_API_KEY: ""
```

完整字段见 `deploy/k8s/secret.yaml.example`。

## Health Probes

**Backend**

| 探针 | 路径 |
|------|------|
| Liveness | `GET /api/health/live` |
| Readiness | `GET /api/health/ready`（PostgreSQL、Redis、ChromaDB） |

**Celery**

- Liveness：`celery -A app.core.celery_app inspect ping`
- Redis heartbeat key：`knowflow:celery:worker:heartbeat`（readiness 可扩展检查）

## Resources 建议

Backend / Celery 已配置示例（可按集群调整）：

```yaml
resources:
  requests:
    cpu: "500m"
    memory: "1Gi"
  limits:
    cpu: "2"
    memory: "4Gi"
```

启用 `local_bge` 后应提高内存 limits。

## 相关章节

- [09 — Prometheus](./09-Prometheus.md)
- [10 — 生产安全](./10-生产安全.md)
