PY ?= python

.PHONY: data cells handcheck model backtest-quick api web test

data: ; $(PY) -m data_pipeline.run
cells: ; $(PY) -m data_pipeline.cells
handcheck: ; $(PY) -m data_pipeline.run --score
model: ; $(PY) -m model.run
backtest-quick: ; $(PY) -m model.run --quick
api: ; $(PY) -m uvicorn backend.app:app --reload --port 8000
web: ; cd frontend && npm run dev
test: ; $(PY) -m pytest -q
