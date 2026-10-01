# 地址校验服务镜像。参考数据（data/，按 README 的脚本构建）体积大、会定期更新，不打进镜像，运行时挂载：
#   docker build -t address-validation .
#   docker run -p 8080:8080 -v $PWD/data:/app/data address-validation
# 可选：带本地小模型（llama.cpp，纯 CPU；模型文件放在 data/models/ 下）
#   docker build --build-arg WITH_LLM=1 -t address-validation:llm .
#   docker run -p 8080:8080 -v $PWD/data:/app/data address-validation:llm \
#     python -m avmvp.server --host 0.0.0.0 --intl-llm data/models/Qwen3-4B-Instruct-2507-Q4_K_M.gguf
FROM python:3.11-slim

ARG WITH_LLM=0
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
 && if [ "$WITH_LLM" = "1" ]; then \
      apt-get update && apt-get install -y --no-install-recommends build-essential cmake \
      && pip install --no-cache-dir llama-cpp-python \
      && apt-get purge -y build-essential cmake && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*; \
    fi

COPY avmvp ./avmvp
COPY scripts ./scripts
COPY models ./models

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz')"
CMD ["python", "-m", "avmvp.server", "--host", "0.0.0.0", "--port", "8080"]
