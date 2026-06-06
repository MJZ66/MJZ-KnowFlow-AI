# KnowFlow AI — 部署与开发文档

> 本文档已拆分为分章版本，便于按主题查阅。

## 中文分章文档（推荐）

**索引入口：** [docs/zh/README.md](./zh/README.md)

| 章节 | 链接 |
|------|------|
| 01 环境与定位 | [01-环境.md](./zh/01-环境.md) |
| 02 本地启动 | [02-本地启动.md](./zh/02-本地启动.md) |
| 03 后端验收 | [03-后端验收.md](./zh/03-后端验收.md) |
| 04 前端验收 | [04-前端验收.md](./zh/04-前端验收.md) |
| 05 数据库检查 | [05-数据库检查.md](./zh/05-数据库检查.md) |
| 06 环境变量 | [06-环境变量.md](./zh/06-环境变量.md) |
| 07 Docker Compose | [07-Docker-Compose.md](./zh/07-Docker-Compose.md) |
| 08 Kubernetes | [08-Kubernetes.md](./zh/08-Kubernetes.md) |
| 09 Prometheus | [09-Prometheus.md](./zh/09-Prometheus.md) |
| 10 生产安全 | [10-生产安全.md](./zh/10-生产安全.md) |
| 11 前端功能 | [11-前端功能.md](./zh/11-前端功能.md) |
| 12 排错 | [12-排错.md](./zh/12-排错.md) |
| 13 团队流程 | [13-团队流程.md](./zh/13-团队流程.md) |
| 14 下一步路线 | [14-下一步路线.md](./zh/14-下一步路线.md) |
| 15 成熟度 | [15-成熟度.md](./zh/15-成熟度.md) |
| 16 最短部署 | [16-最短部署清单.md](./zh/16-最短部署清单.md) |

## 其他

- [deploy/README.md](../deploy/README.md) — K8s 部署专篇
- [README.md](../README.md) — 项目快速开始

## 验收基线（摘要）

```text
e2e_acceptance.py:  13/13
pytest:             63 passed, 2 skipped
npm run build:      pass
npm run test:run:   19 passed
npm run e2e:        4 passed
```
