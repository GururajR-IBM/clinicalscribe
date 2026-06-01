# gateway

Public REST + SSE API surface. JWT auth (Clerk), signed Blob upload URLs, encounter CRUD, live progress streaming.

**Phase:** introduced in Phase 0 as a stub; built out in Phase 1.

## Local dev

```powershell
uv sync
uv run uvicorn gateway.main:app --reload
# http://localhost:8000/docs
```

## Tests

```powershell
uv run pytest
```
