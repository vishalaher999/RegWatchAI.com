# RegWatch AI API (Day 40, KM #229 Docker)
#
# Builds the FastAPI read-API (api/main.py) over the existing SQLite DB +
# data/f3_indexes/*.json. Build/run:
#
#   docker build -t regwatch-api .
#   docker run -p 8000:8000 --env-file .env regwatch-api
#
# Then: curl http://localhost:8000/health
#
# Note: requirements.txt includes sentence-transformers (torch) for F2/F3
# pipeline code, making this a large image (~3-4GB). The API itself never
# imports those modules, so a v2 slim image would split a separate
# requirements-api.txt -- documented in docs/Deployment-Guide-v1.md.

FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
