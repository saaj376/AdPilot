# AdPilot — Video Research and Campaign Planning

Small ecommerce businesses often spend on ads before understanding the problems their customers care about. AdPilot turns YouTube reviews, comparisons, and tutorials into evidence-linked campaign hypotheses that a business can review and test.

## What it does

1. Accept a product description, audience, substantiated product facts, and up to five YouTube videos.
2. Collect captions or accept timestamped transcript excerpts when captions are unavailable.
3. Identify relevant pain points, buying objections, desired features, and purchase questions.
4. Link findings to transcript timestamps and supplied product facts.
5. Suggest keyword ideas, ad drafts, landing-page improvements, and measurable experiments.
6. Export the research brief, or attach it to a campaign plan with a budget and geographic targets.

The campaign planning pipeline has eight agents: research, keyword strategy, creative drafting, policy review, launch-package preparation, measurement readiness, optimization recommendations, and plan summary. Completed plans can be exported as JSON. AdPilot does not publish ads, change bids, or spend money. No advertising account or credentials are required.

## Run locally

See [RUNNING.md](RUNNING.md) for installation, configuration, checks, and limitations.

The app uses React/TypeScript, FastAPI, Redis, Ollama, and youtube-transcript-api. The optional Google Ads MCP reader is a separate read-only bridge, excluded from the planning pipeline. Its isolated runtime is not required for the app.

## API

| Method | Route | Purpose |
| --- | --- | --- |
| POST | `/research` | Start a video research brief |
| GET | `/research/{id}` | Read progress, sources, evidence and findings |
| GET | `/research/{id}/export` | Export a completed research brief |
| POST | `/campaigns` | Generate a campaign plan, optionally with `research_brief_id` |
| GET | `/campaigns` | List saved plan IDs |
| GET | `/campaigns/{id}` | Read a plan and agent outputs |
| GET | `/campaigns/{id}/status` | Read planning progress |
| GET | `/campaigns/{id}/export` | Export a completed plan |
| GET | `/reports/{id}` | Read the plan summary (legacy response field: `weekly_report`) |
| WS | `/live/{id}` | Stream planning progress |
| GET | `/health` | App health |

## Limits

Video opinions are hypotheses, not proof of demand. Captions may be inaccurate or unavailable, and transcripts do not cover visuals or comments. Product claims and the relevance of evidence require human review. Keyword metrics are heuristic estimates. Model and reference validation cannot guarantee factual accuracy.

Redis retains snapshots for seven days by default. Interrupted workers do not resume automatically, and the in-memory event bus supports one backend worker. The scheduler remains a placeholder; recurring jobs are not implemented.
