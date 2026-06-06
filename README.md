# KnowFlow AI — 私有 AI 知识库问答平台

面向个人与小型团队的 RAG 知识库：上传 PDF / DOCX / MD / TXT，自动解析、切片、向量化，基于知识库进行带来源引用的流式问答。

**当前状态：生产可演示 / 准生产 Beta**

| 验收项 | 基线 |
|--------|------|
| `python scripts/e2e_acceptance.py` | 13/13 |
| `pytest tests/` | 55 passed, 2 skipped |
| `npm run build` | pass |
| `npm run test:run` | 19 passed |
| `npm run e2e` | 4 passed（desktop 2 + mobile 2；需 backend + `npx playwright install chromium`） |

完整部署与开发说明见 **[docs/zh/README.md](docs/zh/README.md)**（分章索引）；**最短部署**见 [docs/zh/16-最短部署清单.md](docs/zh/16-最短部署清单.md)；K8s 见 **[deploy/README.md](deploy/README.md)**。

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React + TypeScript + Vite + TailwindCSS + Zustand + i18n |
| 后端 | FastAPI + SQLAlchemy (async) + Celery + JWT |
| 数据 | PostgreSQL 16、Redis 7、ChromaDB |
| 检索 | 向量 + 可选 Hybrid / Reranker；Embedding hash / local_bge |
| 生成 | Qwen / OpenAI-Compatible（SSE） |
| 可观测 | Prometheus `/api/metrics`、健康检查 live/ready |
| 部署 | Docker Compose、K8s 清单、Nginx（production profile） |

## 快速开始

### 1. 环境变量

```powershell
cd knowflow-ai
copy .env.example .env
# 或: copy .env.development.example .env
```

编辑 `.env`：至少配置 `LLM_API_KEY`；开发可用默认 `SECRET_KEY`（生产须 ≥ 32 字符）。

### 2. Docker Compose

```powershell
docker compose up --build -d
# 或一键部署+验收: .\deploy_all.ps1
# 或仅后端: docker compose up --build -d backend celery-worker
# backend 与 celery-worker 共用镜像，改后端代码后须一起重建
```

| 服务 | 地址 |
|------|------|
| 前端 | http://localhost:3000 |
| API | http://localhost:8000 |
| Swagger | http://localhost:8000/docs |
| Metrics | http://localhost:8000/api/metrics |

生产含 Nginx：

```powershell
docker compose --profile production up --build -d
```

### 3. 本地前端 + 浏览器 E2E

```powershell
cd frontend
npm install
npm run dev          # http://localhost:3000
npm run e2e          # 自动启动 dev，无需另开终端
```

### 4. 验收（推荐每次改动后）

```powershell
docker compose up --build -d backend celery-worker

cd backend
python scripts\e2e_acceptance.py
docker compose exec backend pytest tests/ -v

cd ..\frontend
npm run build
npm run test:run
npm run e2e
```

## 架构概览

```text
上传文档 → FastAPI 落盘 → Celery/Background 处理
  → 解析 → 切片 → 向量化 (Chroma) → COMPLETED
用户提问 → 检索 (vector/hybrid) → 过滤 COMPLETED → 可选 rerank
  → LLM 流式 SSE → references + DocumentPreviewPanel
```

## 目录结构（摘要）

```text
knowflow-ai/
├── backend/          # FastAPI, Celery, RAG, alembic, tests
├── frontend/         # React, Playwright e2e, Vitest
├── deploy/k8s/       # Kubernetes 清单
├── docs/
│   ├── DEPLOYMENT_AND_DEVELOPMENT.md
│   └── zh/             # 分章部署与开发文档（推荐）
├── nginx/
└── docker-compose.yml
```

## API 概览

- **认证：** `/api/auth/register|login|refresh|me`
- **知识库：** `/api/kbs`（分页 `{items,total,skip,limit}`）、成员 CRUD
- **文档：** 上传、列表（分页）、状态、`/api/documents/{id}/chunks` 预览
- **对话：** 会话、消息、`/api/chat/sessions/{id}/stream`（SSE）
- **健康：** `/api/health`、`/live`、`/ready`
- **监控：** `/api/metrics`

## 环境模板

| 文件 | 用途 |
|------|------|
| `.env.example` | 默认开发模板 |
| `.env.development.example` | 开发命名模板 |
| `.env.staging.example` | 预发 |
| `.env.production.example` | 生产 |

## 许可证

MIT
