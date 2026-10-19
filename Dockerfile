FROM node:22.13.0-bookworm-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12.3-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 CAREERINSIGHT_AUTO_CREATE=false
WORKDIR /app
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
COPY alembic.ini ./alembic.ini
COPY frontend/ ./frontend/
COPY --from=frontend-build /app/frontend/dist ./frontend/dist
COPY database/ ./database/
COPY ml/ ./ml/
COPY llm/ ./llm/
COPY rag/ ./rag/
EXPOSE 3000
CMD ["sh", "-c", "alembic upgrade head && uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-3000}"]
