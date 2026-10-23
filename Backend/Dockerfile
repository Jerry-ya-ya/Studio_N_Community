# 使用官方 Python 基礎映像（slim 較小）
FROM python:3.11-slim

# 基本環境
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

# ==== 安裝 MS ODBC Driver（新版做法，無 apt-key）====
# 這段適用 Debian 12（bookworm）；若你的基底是 11，將 12/bookworm 改為 11/bullseye
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends curl gnupg ca-certificates apt-transport-https; \
    mkdir -p /etc/apt/keyrings; \
    curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
      | gpg --dearmor -o /etc/apt/keyrings/microsoft.gpg; \
    echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/microsoft.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" \
      > /etc/apt/sources.list.d/microsoft.list; \
    apt-get update; \
    # 建議用 msodbcsql18；若你確定需要 17 再改回 msodbcsql17
    ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 unixodbc; \
    update-ca-certificates; \
    rm -rf /var/lib/apt/lists/*

# Bootstrap pip from the hash-verified wheel published in the Python security
# advisory for the eMudhra/emSign CA incident.
RUN python -m pip install \
    "pip @ https://files.pythonhosted.org/packages/3f/06/3e4420302363fbb71be3c7f35ce042f54bfca330e3e66b3a2e3c4cca579f/pip-26.2.2-py3-none-any.whl#sha256=fd7f4dfa8190e014013b9f08f3e973f4e4c26ffd179a204895533a7254813a70"

# ==== 建置期工具（若需要編譯某些 pip 套件，如 pyodbc、psycopg等）====
# 先裝 build 依賴，pip 完成後再移除，縮小體積
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      build-essential gcc g++ \
      unixodbc-dev \
      libpq-dev; \
    rm -rf /var/lib/apt/lists/*

# 工作目錄
WORKDIR /app

# 先複製需求檔，利用 layer cache
COPY requirements.txt ./

# 安裝 Python 套件（例如 Flask、gunicorn、pyodbc、psycopg、SQLAlchemy 等）
RUN python -m pip install -r requirements.txt

# 複製專案原始碼
COPY . .

# （選擇性）若不再需要編譯器與 dev headers，可在此移除以縮小映像：
# RUN apt-get purge -y build-essential gcc g++ unixodbc-dev libpq-dev && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

# 開放埠（可選）
EXPOSE 5000

# 啟動指令：Gunicorn + 工廠模式
# 注意：app:create_app() 需與你的模組/函式名稱一致
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:create_app()"]
