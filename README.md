# drainfast
Hackathon project for Hackachusetts powered by Kiro

## Run locally

All commands run from the repository root on macOS.

### Setup

Prerequisites: `python3.11` and `node`.

```bash
brew install python@3.11
brew install node
```

Run setup once. It creates `.venv` and installs Python and frontend dependencies. It is safe to rerun.

```bash
./scripts/setup.sh
```

### Development

Run setup first, then:

```bash
./scripts/dev.sh
```

Open http://localhost:5173. Vite proxies the API paths (`/health`, `/brief`, `/backlog`, `/cells`, `/backtest`, `/rain-trend`) to the local API at http://localhost:8000. If `backend/app.py` doesn't exist yet, only the frontend starts and it shows bundled demo data with a "demo data" badge. Press Ctrl+C to stop both.

Optional: to point the frontend at a different API, copy `frontend/.env.example` to `frontend/.env.local` and set `VITE_API_URL`, then restart.

```bash
cp frontend/.env.example frontend/.env.local
```

### Production-like

```bash
./scripts/prod_local.sh
```

Open http://localhost:8000. This builds `frontend/dist` and runs the API, which serves the built frontend. It needs `backend/app.py`.

### Docker

```bash
docker build -t drainfast .
docker run -p 8080:8080 drainfast
```

Open http://localhost:8080. The container listens on port 8080 (not 8000) and runs with fallback mode on by default.

### Fallback mode

```bash
DRAINFAST_FALLBACK=1 ./scripts/dev.sh
```

Fallback mode disables all Bedrock calls. It also works with `DRAINFAST_FALLBACK=1 ./scripts/prod_local.sh`.

### Troubleshooting

| Symptom | Fix |
|---|---|
| Venv not active | Run `./scripts/setup.sh`, then `source .venv/bin/activate` |
| Port 8000 or 5173 busy | The script prints the busy port's process and PID. Stop it, then rerun. Find it with `lsof -nP -iTCP:5173 -sTCP:LISTEN` (or `:8000`) and stop it with `kill $(lsof -t -iTCP:5173 -sTCP:LISTEN)` |
| "demo data" badge showing | The badge means bundled fixture data is shown because the local API isn't answering on port 8000. Start the backend and check `curl localhost:8000/health` |
| `make: command not found` | `xcode-select --install` |
