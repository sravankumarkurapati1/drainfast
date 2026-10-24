---
inclusion: always
---
# Structure and ownership
Each folder has one owner. Only change files inside the module you are working on.
- data_pipeline/, tests/data_pipeline/ : data and labels
- model/, evaluation/, tests/model/ : model and evaluation
- backend/, mcp_server/, tests/backend/ : API, triage, co-pilot, MCP
- frontend/ : UI
- contracts/ : frozen; never edit unless the task explicitly says so
If a task needs a change in another module, stop and say so instead of editing it.