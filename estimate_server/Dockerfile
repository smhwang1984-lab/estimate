FROM python:3.12-slim

WORKDIR /app

ENV TZ=Asia/Seoul \
    PYTHONUNBUFFERED=1 \
    ESTIMATE_PORT=8100 \
    ESTIMATE_DATA_DIR=/data

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 서버 패키지(estimate_server/ 하위 전체). data/·.env는 .dockerignore로 뺀다.
COPY . ./estimate_server/

EXPOSE 8100

CMD ["sh", "-c", "uvicorn estimate_server.app:app --host 0.0.0.0 --port ${ESTIMATE_PORT:-8100}"]
