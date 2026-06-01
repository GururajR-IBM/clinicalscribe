# Contributing to ClinicalScribe

Thanks for your interest. This is a personal portfolio + learning project — PRs welcome,
but expect opinionated reviews against the locked decisions in `docs/adr/`.

## Hard rules

- **No real patient data, ever.** Synthetic only. PRs adding real or scraped clinical data will be closed.
- **No clinical claims.** This is not a medical device. Keep wording cautious.
- **No bypassing the Critic agent** in the orchestrator (Phase 3+).
- **No inline prompts** — all prompts live in `packages/prompts` with a version pin.
- **No secrets in code or CI** — use Entra workload identity / GitHub OIDC.

## Workflow

1. Open an issue describing intent (or pick one).
2. Branch from `main`: `git switch -c feat/<short-name>`.
3. Run the toolchain locally:
   ```powershell
   # python
   uv sync; uv run ruff check .; uv run pytest
   # node
   pnpm install; pnpm -r type-check; pnpm -r lint; pnpm -r test
   # terraform
   terraform -chdir=infra/terraform fmt -recursive -check
   ```
4. Commit with [Conventional Commits](https://www.conventionalcommits.org/) (`pre-commit` enforces it).
5. Open a PR. Fill in the template. CI must be green.

## Local setup

```powershell
# one-time
uv sync
pnpm install
pre-commit install --hook-type commit-msg --hook-type pre-commit
```

## Adding a new service or MCP server

1. Copy the closest existing folder under `services/` or `mcp-servers/`.
2. Update name in `pyproject.toml`, package folder name in `src/`, and module name in `Dockerfile`.
3. Add the path to the matrix in `.github/workflows/ci.yml`.
4. Add a one-paragraph `README.md` describing scope and the phase it goes live.
