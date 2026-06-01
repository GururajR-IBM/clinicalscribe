# prompts

Centralised, versioned agent prompts (Jinja2 templates). Agents load by `(name, version)` — never inline prompts in code. This lets us A/B test and roll back without redeploys.
