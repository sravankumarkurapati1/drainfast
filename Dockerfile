FROM node:20-slim AS web
WORKDIR /app/frontend
COPY frontend/ .
RUN npm ci && npm run build

FROM python:3.11-slim
WORKDIR /app
COPY . .
COPY --from=web /app/frontend/dist frontend/dist
RUN pip install --no-cache-dir -r requirements.txt
# Live mode: real NWS forecast and NOAA tides, no sample data. Bedrock stays off
# unless BEDROCK_MODEL_ID and AWS credentials are provided.
ENV DRAINFAST_FALLBACK=0
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8080"]
