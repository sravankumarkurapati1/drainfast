---
inclusion: always
---
# DrainFast — Tech Stack and Engineering Rules

## Stack
- Language: Python 3.11.
- Data: pandas, pyarrow (Parquet files), numpy.
- Model: scikit-learn (logistic regression or gradient boosting). Keep it explainable.
- API: FastAPI with uvicorn; Pydantic v2 for all request and response models.
- External calls: httpx. AWS: boto3 for Amazon Bedrock.
- MCP server: the official MCP Python SDK, in mcp_server/.
- Tests: pytest and Hypothesis (property-based tests).
- Frontend: React 18, Vite, TypeScript, Leaflet (react-leaflet) for the map.
- Deploy: Docker image for the API; static build for the frontend.

## Data sources
- Boston 311 service requests: data.boston.gov yearly CSVs plus field codebook.
- Hourly rainfall, Boston Logan: NOAA NCEI or Iowa Environmental Mesonet.
- Rain forecast: National Weather Service API (api.weather.gov). Always send a
  User-Agent header identifying DrainFast, as the NWS requires.
- Tides: NOAA gauge 8443970.
- Environmental justice block groups: MassGIS.
- Storage: raw downloads in data/raw/ and processed files in data/processed/
  (both gitignored). A small committed snapshot lives in data/demo/ so the app runs
  for judges without downloads.

## Hard rules
1. Numbers come from code. The LLM may explain or classify, but every count, rate,
   score and ranking shown to users is computed in Python.
2. No data leakage. Features for a storm on date S use only rows dated strictly
   before S. Every feature and training function takes an explicit as_of date and
   never reads today's date implicitly.
3. Determinism. Use random_state=42 everywhere. Sort rankings by score, then by
   location_id, so identical inputs always give identical output.
4. Fallback. When DRAINFAST_FALLBACK=1, make no Bedrock calls: use rule-based labels
   and a template co-pilot answer. The full app must run offline from data/demo/.
5. Contracts. Import models from contracts.schemas and file paths from
   contracts.paths. Never redefine a model or hard-code a data path.
6. Secrets. Read AWS_REGION, AWS_PROFILE and BEDROCK_MODEL_ID from environment
   variables. Never commit keys. .env is gitignored; .env.example is committed.
7. LLM use is limited to (a) labeling closing notes the keyword rules cannot decide
   and (b) co-pilot explanations. Keep prompts in .txt files next to the code that
   uses them. Validate every LLM label against the CauseLabel enum; anything invalid
   becomes "unclear".

## Python conventions
- Type hints on every function. Prefer small, pure functions; no global mutable state.
- snake_case for files and functions, PascalCase for classes.
- One short docstring per public function: what it does, inputs, outputs.
- Use the logging module, never print, outside scripts.
- Timestamps are timezone-aware in America/New_York; storm_day is a date.
- Raise specific exceptions. API errors return JSON {"detail": "..."} with the right
  HTTP status code.

## API conventions
- Endpoints, parameters and response shapes must match contracts/openapi.yaml exactly.
- Use the Pydantic models from contracts.schemas as response_model.
- JSON fields are snake_case.
- CORS allows the frontend origin from the FRONTEND_ORIGIN environment variable.

## Frontend conventions
- All HTTP calls go through frontend/src/api/client.ts. Components never call fetch.
- Fall back to contracts/fixtures data when the API is unreachable.
- Keyboard accessible, color-blind-safe risk colors, readable contrast.

## Testing rules
- Tests live in tests/<module>/ and run offline with DRAINFAST_FALLBACK=1.
- Use Hypothesis for invariants: label values are always valid, no ticket is lost in
  the pipeline or in duplicate merging, no future data in features, rankings are
  deterministic, every brief item has evidence, new work orders are pending_approval.
- make test must pass before any pull request.

## Commands
- make data      build processed data from data/raw
- make train     train the risk model
- make backtest  run the backtest against both baselines
- make api       start the FastAPI server
- make web       start the frontend dev server
- make test      run all tests

## Reference files
API contract: #[[file:contracts/openapi.yaml]]
Schemas: #[[file:contracts/schemas.py]]