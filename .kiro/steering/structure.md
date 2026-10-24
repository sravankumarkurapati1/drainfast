---
inclusion: always
---
# Tech stack and hard rules
- Python 3.11, pandas, scikit-learn, FastAPI, Pydantic, pytest, Hypothesis.
- Frontend: React + Vite + a map library (Leaflet or MapLibre), in frontend/.
- LLM: Amazon Bedrock, only for cause labeling of unclear notes and the co-pilot.
- Every number shown to users comes from code, never from an LLM.
- Training data must always be dated strictly before the storm being tested.
- Every LLM call has a rule-based fallback controlled by DRAINFAST_FALLBACK=1.
- Never hard-code secrets. Read them from environment variables.
- Shared data shapes live in contracts/schemas.py. Import them; never redefine them.
API contract: #[[file:contracts/openapi.yaml]]
Schemas: #[[file:contracts/schemas.py]]