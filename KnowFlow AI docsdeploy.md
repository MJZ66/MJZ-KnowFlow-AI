# KnowFlow AI 部署文档

本文档记录 KnowFlow AI 在阿里云 ECS 上的 Docker Compose 多服务部署过程，覆盖 PostgreSQL、Redis、ChromaDB、FastAPI Backend、React Frontend 与 Celery Worker。

## 1. 项目说明

KnowFlow AI 是一个企业级 RAG 知识库平台，支持文档上传、向量化检索、RAG 问答、多用户管理与知识库运营。

* GitHub：https://github.com/MJZ66/MJZ-KnowFlow-AI
* Demo：http://118.31.70.255:8502
* 后端接口文档：http://118.31.70.255:8000/docs
* 技术栈：FastAPI、React、TypeScript、PostgreSQL、Redis、ChromaDB、Celery、Docker Compose

## 2. 服务器环境

* 云服务器：阿里云 ECS
* 操作系统：Ubuntu 22.04 LTS
* CPU：2 vCPU
* 内存：8 GB
* 公网 IP：118.31.70.255

## 3. 安装基础工具

```bash
apt update && apt upgrade -y
apt install -y git curl wget vim unzip htop net-tools
```

## 4. 安装 Docker 和 Docker Compose

```bash
apt install -y docker.io
systemctl start docker
systemctl enable docker
docker --version
```

如 `docker-compose-plugin` 不可用：

```bash
apt install -y docker-compose
docker-compose --version
```

## 5. 配置 Docker 镜像源

```bash
mkdir -p /etc/docker

cat > /etc/docker/daemon.json <<'EOF'
{
  "registry-mirrors": [
    "https://docker.m.daocloud.io",
    "https://docker.1ms.run",
    "https://docker.xuanyuan.me"
  ]
}
EOF

systemctl daemon-reload
systemctl restart docker
```

## 6. 获取项目代码

如果 `git clone` 失败，可使用 zip 下载：

```bash
cd /opt/projects
wget -O knowflow.zip https://github.com/MJZ66/MJZ-KnowFlow-AI/archive/refs/heads/main.zip
unzip knowflow.zip
mv MJZ-KnowFlow-AI-main MJZ-KnowFlow-AI
cd MJZ-KnowFlow-AI
```

## 7. 服务组成

KnowFlow AI 使用 Docker Compose 编排以下服务：

| 服务              | 作用        |
| --------------- | --------- |
| PostgreSQL      | 业务数据存储    |
| Redis           | 缓存与任务队列   |
| ChromaDB        | 向量数据库     |
| FastAPI Backend | 后端 API 服务 |
| React Frontend  | 前端页面      |
| Celery Worker   | 异步任务处理    |

## 8. 配置环境变量

在项目根目录创建 `.env`：

```bash
cat > .env << 'EOF'
POSTGRES_USER=knowflow
POSTGRES_PASSWORD=knowflow123
POSTGRES_DB=knowflow

SECRET_KEY=your_generated_secret_key

LLM_PROVIDER=qwen
LLM_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_API_KEY=your_api_key
LLM_MODEL=qwen-plus

DEEPSEEK_API_KEY=your_deepseek_api_key

BACKEND_PORT=8000
FRONTEND_PORT=8502

APP_ENV=production
EOF
```

生产环境建议生成随机 SECRET_KEY：

```bash
openssl rand -hex 32
```

然后替换：

```env
SECRET_KEY=生成的随机字符串
```

## 9. 修改 Debian 软件源

如果后端构建时 `apt-get update` 较慢，可修改 `backend/Dockerfile`。

在：

```dockerfile
FROM python:3.12-slim
```

后添加：

```dockerfile
RUN sed -i 's|http://deb.debian.org/debian|https://mirrors.tuna.tsinghua.edu.cn/debian|g' /etc/apt/sources.list.d/debian.sources && \
    sed -i 's|http://deb.debian.org/debian-security|https://mirrors.tuna.tsinghua.edu.cn/debian-security|g' /etc/apt/sources.list.d/debian.sources
```

## 10. 构建并启动

完整启动：

```bash
docker-compose up -d
```

只启动核心服务：

```bash
docker-compose up -d postgres redis chromadb backend frontend
```

## 11. 查看容器状态

```bash
docker-compose ps
```

正常状态示例：

```text
knowflow-backend         Up (healthy)
knowflow-celery-worker   Up
knowflow-chromadb        Up (healthy)
knowflow-frontend        Up
knowflow-postgres        Up (healthy)
knowflow-redis           Up (healthy)
```

查看后端日志：

```bash
docker-compose logs --tail=120 backend
```

正常日志应包含：

```text
Application startup complete.
```

## 12. 阿里云安全组配置

前端访问端口：

```text
协议类型：自定义 TCP
端口范围：8502/8502
授权对象：0.0.0.0/0
```

后端接口端口：

```text
协议类型：自定义 TCP
端口范围：8000/8000
授权对象：0.0.0.0/0
```

正式生产环境中，不建议将以下端口暴露公网：

```text
5432 PostgreSQL
6379 Redis
8001 ChromaDB
```

## 13. 服务验证

### 13.1 验证前端

```bash
curl http://localhost:8502
```

正常情况下会返回前端 HTML。

浏览器访问：

```text
http://118.31.70.255:8502
```

### 13.2 验证后端

```bash
curl http://localhost:8000/api/health/live
```

正常返回：

```json
{"status":"alive"}
```

后端文档：

```text
http://118.31.70.255:8000/docs
```

## 14. 常见问题

### 14.1 GitHub clone 失败

错误：

```text
RPC failed; curl 16 Error in the HTTP2 framing layer
GnuTLS recv error (-110)
```

解决：

```bash
wget -O knowflow.zip https://github.com/MJZ66/MJZ-KnowFlow-AI/archive/refs/heads/main.zip
unzip knowflow.zip
```

### 14.2 Debian 源下载慢

后端 Dockerfile 中 `apt-get update` 卡住时，替换为清华 Debian 源。

### 14.3 SECRET_KEY 不安全

错误：

```text
RuntimeError: SECRET_KEY is insecure for production.
```

解决：

```bash
openssl rand -hex 32
nano .env
docker-compose down
docker-compose up -d
```

### 14.4 容器显示创建成功，但服务不可用

不要只看：

```text
Creating ... done
```

还需要检查：

```bash
docker-compose ps
docker-compose logs --tail=120
```

确认服务为：

```text
Up (healthy)
```

### 14.5 前端能本地访问，公网打不开

先验证本机服务：

```bash
curl http://localhost:8502
```

如果本机正常，通常是阿里云安全组未放行 8502。

## 15. 常用运维命令

```bash
docker-compose ps
docker-compose logs --tail=120
docker-compose logs -f
docker-compose restart
docker-compose restart backend
docker-compose down
docker-compose up -d --build
```

## 16. 部署结果

KnowFlow AI 已成功部署至阿里云 ECS，并通过公网访问：

```text
前端：
http://118.31.70.255:8502

后端接口文档：
http://118.31.70.255:8000/docs
```

本次部署完成了企业级 RAG 知识库系统从代码构建、多容器编排、服务健康检查到公网访问验证的完整流程。
