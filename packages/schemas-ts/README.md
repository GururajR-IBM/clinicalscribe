# schemas-ts

Zod schemas mirroring `packages/schemas-py`. Consumed by `apps/web`. Keep field names camelCased; Pydantic side uses snake_case with `model_config = ConfigDict(alias_generator=...)` at the API boundary (Phase 1).
