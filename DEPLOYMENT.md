# Deployment Runbook

## Phase 1 — GitHub

1. Create an empty GitHub repository: `sme-loan-onboarding-agent`.
2. From this project directory run:

```powershell
git init -b main
git add .
git commit -m "Initial SME loan onboarding agent"
git remote add origin https://github.com/YOUR_USERNAME/sme-loan-onboarding-agent.git
git push -u origin main
```

3. Confirm that `.env` is not tracked.

## Phase 2 — Streamlit demo

Deploy `streamlit_app.py` from the GitHub repository. If using a hosted deployment, add `ANTHROPIC_API_KEY` and `CLAUDE_MODEL` through the platform's secrets/environment-variable mechanism rather than committing them to Git.

For the first deployment, the app intentionally uses synthetic data and in-memory checkpointing.

## Phase 3 — Production architecture

Move the graph behind an API service and replace `MemorySaver` with a durable PostgreSQL-backed checkpointer. Add authentication, authorization, audit logging, idempotency keys, external-system retry controls, policy versioning, observability and human-approval controls before connecting real lending systems.
