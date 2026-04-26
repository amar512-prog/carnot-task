FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY config ./config
COPY data ./data
COPY docs ./docs
COPY sql ./sql
COPY tests ./tests
COPY scripts ./scripts

RUN pip install --no-cache-dir .

CMD ["uvicorn", "demo.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

