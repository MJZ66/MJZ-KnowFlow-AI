FROM python:3.12-slim

WORKDIR /app

ARG INSTALL_BGE=false

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

COPY requirements-bge.txt .
RUN if [ "$INSTALL_BGE" = "true" ]; then \
      pip install --no-cache-dir -r requirements-bge.txt \
        -i https://pypi.tuna.tsinghua.edu.cn/simple \
        --extra-index-url https://download.pytorch.org/whl/cpu ; \
    fi

COPY . .

RUN mkdir -p /app/uploads && \
    python -c "p=open('/app/entrypoint.sh','rb').read().replace(b'\r\n',b'\n').replace(b'\r',b'\n'); open('/app/entrypoint.sh','wb').write(p)" && \
    chmod +x /app/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
