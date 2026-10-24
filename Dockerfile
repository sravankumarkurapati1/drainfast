FROM node:20-slim AS web
WORKDIR /app/frontend
COPY frontend/ .
RUN npm ci && npm run build

FROM python:3.11-slim
WORKDIR /app
COPY . .
COPY --from=web /app/frontend/dist frontend/dist
RUN pip install --no-cache-dir -r requirements.txt
ENV DRAINFAST_FALLBACK=1
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8080"]
