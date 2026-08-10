# ---- Base ----
# Dùng Python 3.12 ổn định (không dùng 3.14 vì nhiều wheel chưa hỗ trợ đầy đủ).
FROM python:3.12-slim

# Biến môi trường cho Python & vị trí lưu model rembg
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    U2NET_HOME=/models/u2net

WORKDIR /app

# Thư viện hệ thống onnxruntime / numba cần (OpenMP runtime)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Cài dependencies trước (tận dụng cache layer khi code thay đổi)
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Tải sẵn model u2net (~176MB) vào image để request đầu tiên không phải chờ tải
RUN python -c "from rembg import new_session; new_session('u2net')"

# Copy source code
COPY . .

EXPOSE 8000

# Chạy server. --app-dir src để code trong src/ import được (from api..., from service...).
# Mặc định 1 worker vì mỗi worker load 1 bản model vào RAM (~200MB).
CMD ["uvicorn", "main:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000"]
