# Running AdPilot

Use Python 3.11 and Node 22.12+ (or Node 24). From the repository root:

```bash
uv venv --python 3.11 backend/.venv
uv pip install --python backend/.venv/bin/python -r backend/requirements.txt
cp backend/.env.example backend/.env
npm --prefix frontend ci
```

Configure `REDIS_URL` and `OLLAMA_MODEL` in `backend/.env`. Use an installed Ollama model or run `ollama pull gemma3:4b`. The environment file is resolved relative to the backend directory. No advertising account credentials are needed.

Start Redis and Ollama, then run these in separate terminals:

```bash
DEBUG=false backend/.venv/bin/python -m uvicorn main:app --app-dir backend --reload
npm --prefix frontend run dev
```

Open http://localhost:5173. `DEBUG=false` overrides shells that export a nonboolean DEBUG value.

## Video research

Enter a product, audience, and up to 15 facts you can substantiate. Add one to five YouTube links. Caption fetching tries English and Hindi by default; API callers can supply a `languages` list.

If captions are blocked or unavailable, paste timed excerpts in the transcript fallback:

```text
[02:15] Replacement filters cost more than I expected.
[03:10] Cleaning pet hair out of the brush takes too long.
```

Each source is limited to an initial 160 snippets or its share of a 12,000-character budget. Truncation and user-supplied transcripts are labeled. Generated evidence IDs and product-fact references are validated. You must still review the interpretation and all product claims.

Export the brief as JSON, or choose **Prepare campaign plan**. The plan uses the research, product facts, planning budget, and geographic targets to draft keywords, ad copy, and an experiment summary. All eight agents run: Research, Keyword, Creative, QA, Launch, Monitor, Optimize, and Report. Launch prepares a draft package; Monitor defines measurement readiness and marks absent metrics unavailable; Optimize recommends experiments without applying changes. The process ends with a downloadable plan; it never publishes anything. Older response fields such as `weekly_report`, `performance_data`, and historical status values remain readable for stored records.

## Checks

```bash
DEBUG=false OTEL_SDK_DISABLED=true backend/.venv/bin/python -m pytest backend/tests -q
npm --prefix frontend run lint
npm --prefix frontend run build
npm --prefix frontend audit
```

Local model integration tests are opt-in using `RUN_FULL_AGENT_FLOW_TEST=1` or `RUN_OLLAMA_AGENT_TESTS=1`. Default tests use deterministic model responses.

## Optional read-only MCP bridge

`backend/tools/google_ads_mcp_reader.py` and `backend/scripts/setup_mcp_runtime.sh` remain available for separate read-only account queries. They are not part of campaign planning and are not needed to use AdPilot. The optional subprocess runs in an isolated runtime and may have its own provider dependencies.

To use it, run `bash backend/scripts/setup_mcp_runtime.sh`, then configure `GOOGLE_APPLICATION_CREDENTIALS` (ADC JSON), `GOOGLE_PROJECT_ID`, and `GOOGLE_ADS_DEVELOPER_TOKEN`. Live read tests require `RUN_GOOGLE_ADS_LIVE_TESTS=1`.

## Limits

Captions can be blocked or inaccurate; this app does not analyze video imagery, direct audio, comments, view counts, or trend popularity. Video opinions are not representative market research. Keyword volumes and CPC are heuristic estimates. Verify product claims and test hypotheses against actual business outcomes.

Redis snapshots expire after seven days by default. Keep research URLs to revisit briefs. Interrupted workers do not resume automatically; run one backend worker for live events. The scheduler is a placeholder and does not run recurring research or campaigns.
