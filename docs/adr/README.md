# Architecture Decision Records

ADRs document binding decisions and their rationale. Each ADR is immutable once accepted;
changing direction means adding a new ADR that supersedes the old one.

Format: [MADR 3.0](https://adr.github.io/madr/) — short.

| #    | Title                                                      | Status   |
| ---- | ---------------------------------------------------------- | -------- |
| 0001 | Overall architecture and agent topology                    | Stub     |
| 0002 | Microsoft Agent Framework as the orchestration runtime     | Pending  |
| 0003 | MCP for tool surfaces                                      | Pending  |
| 0004 | Polyglot persistence (Cosmos NoSQL + Postgres Flexible)    | Pending  |
| 0005 | Clerk for end-user auth (with documented migration path)   | Pending  |
| 0006 | Terraform (not Bicep) for IaC                              | Stub     |
| 0007 | APIM Consumption as the AI gateway (introduced in Phase 6) | Pending  |
| 0008 | Synthetic-only data; no PHI; not for clinical use          | Pending  |

> **Reminder:** ADRs 0001 and 0004 are the core "interview defensibility" docs.
> Draft these properly with **Claude Opus 4.7** before the project is shown externally.
