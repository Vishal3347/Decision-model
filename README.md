# Decision Intelligence Simulator — Streamlit Edition

A Streamlit port of the original Next.js + FastAPI Decision Intelligence Simulator. It reuses the original Python decision engine, scoring, policy validation, simulated tools, orchestrator, SQLite schema, seeded demo data, scenario engine, and briefing generator.

## Features

- Executive Dashboard with KPIs, priority distribution, task completion, decision distribution, pending decisions and recent activity
- Smart Inbox with search, category/priority/status filters, sorting, per-email processing and autonomous vs human-controlled comparison
- Decision Models: expected utility, satisficing, decision tree, weighted matrix, policy rules, educational MDP view, human-in-the-loop gates and agent loop trace
- Approval Centre: approve, reject and modify proposed tool parameters; modified actions are revalidated by the original backend
- Repeatable demo scenarios and run-all workflow
- Activity timeline and generated executive briefing
- Autonomous / Human-controlled operating modes
- Deterministic mock provider by default; no API key required

All external actions remain simulated. No real email is sent, no payment is processed, no contract is signed and no records are deleted.

## Run locally

Python 3.11+ recommended.

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Open the local URL printed by Streamlit (usually http://localhost:8501).

## Deploy free on Streamlit Community Cloud

1. Create a GitHub repository and upload the contents of this folder (the `streamlit_app.py`, `requirements.txt`, `backend/`, and `.streamlit/` must be at the repository root).
2. Visit https://share.streamlit.io/ and sign in with GitHub.
3. Choose **Create app**, select your repository and branch.
4. Set **Main file path** to `streamlit_app.py`.
5. Deploy. No secrets are required for the deterministic mock mode.

## Optional LLM provider

The deterministic mock mode is the default and is recommended for a reliable public demo. The backend supports Gemini/Groq via its original provider factory. Configure provider environment variables in Streamlit app Secrets only if you intentionally want live LLM calls. Never commit API keys.

## Notes and deployment limitations

- Streamlit Community Cloud free apps may sleep when inactive and have resource limits.
- The SQLite database is stored at `/tmp/decision_intelligence_simulator.db` in this deployment. It is demo state, not durable production storage; it may reset when the app restarts or its environment is recycled.
- The app is a single-user educational demo with no authentication, matching the original project's stated scope.
- The MDP view is educational only: it derives reward/Q-value displays from expected utility; it does not train a reinforcement-learning policy.

## Original architecture retained

The `backend/app` modules are retained from the source project. Streamlit calls the same `Services`, `Orchestrator`, `Database`, schema validation, and engine modules directly, rather than replacing decision logic with placeholder calculations.
