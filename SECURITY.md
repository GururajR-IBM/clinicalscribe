# ClinicalScribe — Security Policy

## Reporting a vulnerability

If you discover a security vulnerability, please **do not** open a public issue.

Email: **Gururajraibagi7@gmail.com** with subject `[SECURITY] clinicalscribe: <short summary>`.

You should expect an acknowledgement within 72 hours.

## Scope

This is an educational portfolio project. The following are considered out of scope:

- Issues that require real PHI to reproduce (this project does not handle real PHI).
- Issues only present in default Clerk / Azure SDK configurations.
- Self-XSS or social-engineering vectors.

## Secret handling

- No secrets are committed to this repo. Pre-commit hooks scan for AWS / Azure / generic API key patterns.
- All Azure authentication uses **Workload Identity Federation** (no static credentials in CI).
- All runtime secrets are stored in **Azure Key Vault** and read via Workload Identity from AKS pods.
- Clerk JWT public keys are fetched dynamically from the issuer's JWKS endpoint.

## Responsible AI

This project is a research artifact for studying responsible AI patterns. It is **not** validated for clinical use. See [LICENSE](LICENSE) for the non-clinical-use rider.
