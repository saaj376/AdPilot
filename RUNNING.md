# Running and verifying AdPilot

Use Python 3.11 and Node 22.12+ (or Node 24). From the repository root:

```bash
uv venv --python 3.11 backend/.venv
uv pip install --python backend/.venv/bin/python -r backend/requirements.txt
cp backend/.env.example backend/.env
npm --prefix frontend ci
```

Configure `backend/.env` with your Google Ads credentials and customer ID. The file is resolved relative to the backend directory, regardless of where you launch the server. Set `DEBUG=false` if your shell exports a nonboolean `DEBUG` value. Set `OLLAMA_MODEL` to a locally installed model or run `ollama pull gemma3:4b`. Redis must be reachable at `REDIS_URL`.

For performance monitoring, install the separate Google Ads MCP runtime:

```bash
bash backend/scripts/setup_mcp_runtime.sh
```

Set `GOOGLE_APPLICATION_CREDENTIALS` to an ADC credentials JSON file and `GOOGLE_PROJECT_ID` to your project. OAuth desktop client secrets are a different file; generate the SDK refresh token using `backend/.venv/bin/python backend/oauth.py /path/to/client_secret.json`.

Start the two processes in separate terminals:

```bash
DEBUG=false backend/.venv/bin/python -m uvicorn main:app --app-dir backend --reload
npm --prefix frontend run dev
```

Open http://localhost:5173. Supply the business website as the landing page. Separate locations with semicolons so city/state names retain their commas. Campaigns are created **paused**; completion of the setup pipeline does not enable spending.

Run checks without live advertising writes:

```bash
DEBUG=false OTEL_SDK_DISABLED=true backend/.venv/bin/python -m pytest backend/tests -q
npm --prefix frontend run lint
npm --prefix frontend run build
npm --prefix frontend audit
```

## Current limits

- External integration tests are opt-in and require the documented service credentials and flags in their test files. Passing the default suite verifies orchestration, APIs and SDK request construction; it does not verify a live Google Ads account.
- The daily scheduler is currently a placeholder. Recurring monitoring, optimization and weekly report delivery are not implemented. The initial pipeline runs these steps once.
- Redis stores completed task snapshots for seven days. It does not resume interrupted workers after a restart. The in-memory event bus supports one backend worker.
- A freshly created, paused campaign has no performance history. Zero metrics are expected until the campaign is enabled in Google Ads and receives traffic.
- Keyword volumes/CPC are heuristic estimates, not Keyword Planner measurements. Unavailable competitor searches return explicitly unverified placeholders.
- Google Ads operations are separate writes. A later failure can leave a partially created paused campaign for review in Google Ads; operations are not automatically rolled back.


## Video research workflow

The home page is now the research workspace. Enter a product, a specific audience, and up to 15 product facts you can substantiate. Add one to five YouTube watch, Shorts, live, or youtu.be links. Automatic caption fetching tries English and Hindi by default; the API accepts a `languages` list for other caption languages.

If YouTube blocks caption retrieval or a video has no captions, expand the transcript fallback and paste lines such as:

```text
[02:15] The replacement filters cost more than I expected.
[03:10] Cleaning pet hair out of the brush takes too long.
```

The app preserves timestamped source excerpts, validates the generated JSON, rejects invented evidence IDs or product-fact references, and labels unmapped problems as research gaps. It limits each video to an initial 160 snippets or its share of a 12,000-character analysis budget and displays when that truncation occurs. Manually pasted excerpts are labeled user-supplied; their accuracy is not independently verified.

A completed brief can be exported as JSON or attached to a new paused campaign. The handoff pre-fills product facts and audience and passes the brief's evidence-linked hypotheses into campaign research. Google Ads credentials are needed only for the campaign launch path; research needs Redis and a running Ollama model. Nothing is published by building or exporting a brief.

API routes:

- `POST /research` accepts `product_name`, `product_description`, `audience`, `product_facts`, `videos` (`url` and optional `transcript`), and optional `languages`.
- `GET /research/{id}` returns source availability, status, evidence, and the completed analysis. Keep the brief URL to revisit it within the Redis TTL.
- `GET /research/{id}/export` downloads a completed brief.
- `POST /campaigns` accepts an optional `research_brief_id` referring to a completed brief.

Caption collection uses [youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api). Captions can be unavailable or blocked. This version does not analyze video imagery, audio directly, comments, view counts, or trend popularity. The model checks reference integrity; semantic relevance and product-claim accuracy still require human review. Video opinions are not representative market research or proof of demand. Test the resulting hypotheses using real campaign outcomes.
