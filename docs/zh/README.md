# KnowFlow AI — 中文文档索引

> **项目路径：** `E:\AI知识平台\knowflow-ai`  
> **状态：** 生产可演示版 / 准生产 Beta  
> **验收基线：** e2e 13/13 · pytest 37 passed · build ✓ · Vitest 12 · Playwright 2

本目录将部署与开发说明拆分为可单独查阅的章节。K8s 操作细节另见 [deploy/README.md](../../deploy/README.md)。

---

## 文档目录

| 章节 | 文件 | 内容概述 |
|------|------|----------|
| 01 | [01-环境.md](./01-环境.md) | 项目定位、目录结构、已完成能力、验收基线 |
| 02 | [02-本地启动.md](./02-本地启动.md) | 后端、前端、Playwright 一键 E2E 启动 |
| 03 | [03-后端验收.md](./03-后端验收.md) | `e2e_acceptance.py`、pytest、检索质量脚本 |
| 04 | [04-前端验收.md](./04-前端验收.md) | build、Vitest、Playwright |
| 05 | [05-数据库检查.md](./05-数据库检查.md) | documents / tasks / chunks SQL 检查 |
| 06 | [06-环境变量.md](./06-环境变量.md) | 基础、队列、缓存、Embedding、Hybrid、Reranker、Metrics |
| 07 | [07-Docker-Compose.md](./07-Docker-Compose.md) | Compose 开发/生产、端口、迁移 |
| 08 | [08-Kubernetes.md](./08-Kubernetes.md) | 清单、apply 顺序、Secret、探针、资源 |
| 09 | [09-Prometheus.md](./09-Prometheus.md) | `/api/metrics`、指标、scrape、Grafana 建议 |
| 10 | [10-生产安全.md](./10-生产安全.md) | SECRET_KEY、CORS、上传、密钥管理 |
| 11 | [11-前端功能.md](./11-前端功能.md) | 页面路由、能力清单、后续增强 |
| 12 | [12-排错.md](./12-排错.md) | 常见问题与处理 |
| 13 | [13-团队流程.md](./13-团队流程.md) | 固定验收流程、Commit 规范 |
| 14 | [14-下一步路线.md](./14-下一步路线.md) | 优先级开发路线 |
| 15 | [15-成熟度.md](./15-成熟度.md) | 成熟度评估与剩余差距 |
| 16 | [16-最短部署清单.md](./16-最短部署清单.md) | 全 Docker / 开发模式最短部署步骤 |

---

## 快速入口

**第一次本地跑通：**

1. [02 — 本地启动](./02-本地启动.md)
2. [03 — 后端验收](./03-后端验收.md) + [04 — 前端验收](./04-前端验收.md)

**准备上线 / 一键部署：**

1. [16 — 最短部署清单](./16-最短部署清单.md)（推荐先看）
2. [06 — 环境变量](./06-环境变量.md) → [10 — 生产安全](./10-生产安全.md)
3. [07 — Docker Compose](./07-Docker-Compose.md) 或 [08 — Kubernetes](./08-Kubernetes.md)
4. [09 — Prometheus](./09-Prometheus.md)

**日常开发：**

- [13 — 团队流程](./13-团队流程.md)
- [12 — 排错](./12-排错.md)

---

## 一键验收（复制执行）

```powershell
cd E:\AI知识平台\knowflow-ai
docker compose up --build -d backend celery-worker

cd backend
python scripts\e2e_acceptance.py
docker compose exec backend pytest tests/ -v

cd ..\frontend
npm run build
npm run test:run
npm run e2e
```

---

## 其他文档

- [DEPLOYMENT_AND_DEVELOPMENT.md](../DEPLOYMENT_AND_DEVELOPMENT.md) — 单页汇总（指向本索引）
- [项目根 README](../../README.md) — 快速开始
