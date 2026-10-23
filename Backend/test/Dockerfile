# Dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# 常見：psycopg(或 psycopg2) 需要編譯/系統套件。這裡放最常用的一組。
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    gcc \
    libpq-dev \
 && update-ca-certificates \
 && rm -rf /var/lib/apt/lists/*

RUN python -m pip install \
    "pip @ https://files.pythonhosted.org/packages/3f/06/3e4420302363fbb71be3c7f35ce042f54bfca330e3e66b3a2e3c4cca579f/pip-26.2.2-py3-none-any.whl#sha256=fd7f4dfa8190e014013b9f08f3e973f4e4c26ffd179a204895533a7254813a70"

COPY requirements.txt ./
RUN python -m pip install -r ./requirements.txt

# 複製專案（假設 Dockerfile 在 backend 根目錄）
COPY . .

# 預設不寫測試指令（你說不用幫你寫執行測試指令）
# 你可以用 docker compose run --rm pytest pytest
CMD ["python", "-c", "print('Test image ready. Run pytest via docker compose.')"]
