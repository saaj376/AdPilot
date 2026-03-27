# AdPilot — Autonomous Google Ads Campaign Lifecycle Manager

AdPilot is a fully autonomous, multi-agent AI system that manages the complete Google Ads campaign lifecycle for small and medium-sized businesses. Starting from a single plain-English business description, it researches the market, builds a keyword strategy, writes ad copy, enforces Google Ads policy compliance, launches a live campaign, monitors performance, optimises bids and budgets, and delivers a plain-English weekly report — all without manual intervention.

---

## Table of Contents

1. [Why This Was Built](#why-this-was-built)
2. [What It Does](#what-it-does)
3. [System Architecture](#system-architecture)
4. [The Eight Agents](#the-eight-agents)
5. [How Agents Communicate — The Campaign Context](#how-agents-communicate--the-campaign-context)
6. [Google Ads Integration — Two Distinct Mechanisms](#google-ads-integration--two-distinct-mechanisms)
7. [The Google Ads MCP Server](#the-google-ads-mcp-server)
8. [Real-Time Pipeline Updates — WebSocket and Event Bus](#real-time-pipeline-updates--websocket-and-event-bus)
9. [Backend Technology Stack](#backend-technology-stack)
10. [Frontend Technology Stack](#frontend-technology-stack)
11. [API Reference](#api-reference)
12. [Project Structure](#project-structure)
13. [Prerequisites](#prerequisites)
14. [Installation and Setup](#installation-and-setup)
15. [Environment Variables](#environment-variables)
16. [Running the Application](#running-the-application)
17. [License](#license)

---

## Why This Was Built

Small businesses abandon Google Ads at a high rate. The platform is powerful, but managing it effectively requires a skill set that most small business owners do not have the time to develop. A single campaign demands ongoing attention to keyword research, competitive analysis, ad copywriting, policy compliance, bid optimisation, performance monitoring, and stakeholder reporting. Each of those disciplines is a specialty in its own right.

The goal of AdPilot was to show how modern AI agents — each with a narrow, well-defined responsibility — can collectively handle the full advertising lifecycle in a way that is transparent, auditable, and genuinely useful. Rather than a single large AI prompt trying to do everything, AdPilot decomposes the problem into eight focused agents that each excel at one task and pass structured outputs to the next agent in the chain.

The project is also a practical demonstration of the Model Context Protocol (MCP), specifically the official Google Ads MCP server from Google. The MCP server gives the monitoring agent a clean, structured way to query live campaign performance data using Google Ads Query Language (GAQL) without writing low-level API client code.

---

## What It Does

A user provides three inputs: a free-text description of their business, a monthly budget in USD, and a list of geographic target locations. AdPilot then runs the following end-to-end process automatically:

1. Researches the business and its competitors using web scraping.
2. Builds a keyword strategy organised by intent-based ad groups.
3. Writes Google Ads-compliant headlines and descriptions for every ad group.
4. Reviews and corrects ad copy against Google Ads editorial policies.
5. Creates the full campaign structure — campaign, ad groups, keywords, and responsive search ads — inside a real Google Ads account using the official Python SDK.
6. Reads back live campaign performance data (impressions, clicks, CTR, CPC, spend, conversions) using the Google Ads MCP server.
7. Adjusts keyword bids, pauses underperforming keywords, and reallocates budget based on the performance data.
8. Produces a plain-English weekly performance summary for the business owner.

Every agent step is streamed in real time to a React frontend dashboard over WebSocket so the user can watch the pipeline progress.

---

## System Architecture

```
User Input (business description, monthly budget, geo targets)
         |
         v
POST /campaigns  (FastAPI — HTTP 202 Accepted)
         |
         v
BackgroundTasks  (non-blocking — response returns immediately)
         |
         v
run_crew()  (core/crew.py — orchestration entry point)
         |
         v
CrewAI Crew  (Process.sequential — one agent at a time)
         |
    _____|_______________________________________
   |       |        |      |      |      |      |
Research Keyword Creative  QA  Launch Monitor Optimize  Report
Agent    Agent   Agent   Agent  Agent   Agent   Agent    Agent
   |       |        |      |      |      |      |      |
   |_______|________|______|______|______|______|______|
                           |
                  CampaignContext (shared state)
                           |
                       Redis (persistence)
                           |
                     EventBus (in-memory)
                           |
                    WebSocket /live/{campaign_id}
                           |
                   React Frontend Dashboard
```

The pipeline is sequential — agents run one after another in a fixed order. Each agent reads what previous agents wrote into the shared `CampaignContext` object and adds its own output. The context is persisted to Redis after every agent step so that progress is never lost if the server restarts.

---

## The Eight Agents

### 1. Research Agent

**Role:** Business Research Specialist

**Responsibility:** Analyse the business description and scrape competitor websites to produce a structured business profile.

**Tools:** `scrape_website` and `search_competitors` (HTTP scraping tools built on `httpx` and `BeautifulSoup4`).

**Output written to CampaignContext:** `business_profile` — a structured JSON object containing the business name, business type, location, target audience, unique selling proposition (USP), brand tone, competitor names, buying intent signals, and ad themes.

**Why it matters:** Every downstream agent depends on this output. The keyword agent uses the buying intent signals as seed keywords. The creative agent uses the tone and USP to write copy. The report agent uses the business name in the weekly summary.

---

### 2. Keyword Agent

**Role:** Google Ads Keyword Strategist

**Responsibility:** Build a keyword strategy using intent-based groupings, with search volume and CPC estimates for each keyword.

**Tools:** `get_keyword_ideas` — a heuristic keyword expansion tool. It takes seed keywords from the business profile and generates expanded keyword variants with estimated monthly search volume, CPC, and competition level. The estimates are heuristic (deterministic scoring based on keyword text) so the pipeline works without requiring Google Keyword Planner API access.

**Output written to CampaignContext:** `keyword_strategy` — ad groups with associated keywords, each carrying text, estimated volume, CPC, and competition.

**Design decision:** The heuristic approach was chosen deliberately so the system functions in environments where Google Keyword Planner access (which requires a billing-active account) is not available. The structure of the output is identical to what a live Keyword Planner integration would produce, making a swap straightforward.

---

### 3. Creative Agent

**Role:** Google Ads Copywriter

**Responsibility:** Write compliant headlines and descriptions for every ad group in the keyword strategy.

**Tools:** None. This is a pure LLM agent. It reads the business profile and keyword strategy from the task context and generates ad copy within Google's character limits (30 characters per headline, 90 characters per description).

**Output written to CampaignContext:** `ad_creatives` — per-ad-group copy including headlines, descriptions, and call-to-action text.

**Implementation note:** The agent has `use_system_prompt=False` set. This disables CrewAI's default ReAct (Reasoning + Acting) system prompt so the model produces a direct `Final Answer` without going through the action/observation loop, which would be unnecessary and error-prone for a pure writing task.

---

### 4. QA Agent

**Role:** Google Ads Policy Compliance Reviewer

**Responsibility:** Review every headline and description against Google Ads editorial policies. Automatically fix violations. Return the corrected copy to LaunchAgent.

**Tools:** None. Pure LLM agent with `use_system_prompt=False`.

**Checks performed:** Excessive capitalisation, superlatives without substantiation, misleading claims, punctuation violations, repetition across headlines, and character limit overruns. Violations that would cause automatic disapproval are fixed. Policy warnings are noted but do not block launch.

**Output written to CampaignContext:** `qa_result` — approval status, list of issues found, list of warnings, and `fixed_copy` containing the corrected version of every ad group's copy. LaunchAgent uses `fixed_copy`, never the original.

---

### 5. Launch Agent

**Role:** Google Ads Campaign Launch Specialist

**Responsibility:** Create the full campaign structure in a real Google Ads account using the approved keyword strategy and corrected ad copy.

**Tools:** `create_campaign`, `create_ad_group`, and `create_ads` — Google Ads SDK write tools.

**Execution order:** The agent follows a strict creation order because each step requires the ID from the previous step:

1. `create_campaign` — creates the campaign and its daily budget, returns `campaign_id`.
2. `create_ad_group` — creates one ad group per theme using the `campaign_id`, returns `ad_group_id` for each.
3. `create_ads` — creates a Responsive Search Ad in each ad group using `ad_group_id`.

**Campaign default state:** All campaigns are created as `PAUSED`. No money is spent until the campaign is manually enabled by the account owner. This is an intentional safety measure.

**Output written to CampaignContext:** `campaign_ids` — campaign ID, ad group IDs, and ad IDs returned by the Google Ads API.

---

### 6. Monitor Agent

**Role:** Campaign Performance Analyst

**Responsibility:** Fetch this week's live campaign performance data from Google Ads and identify the top and bottom performing keywords.

**Tools:** `mcp_list_accessible_customers` and `mcp_reader` — these are the two tools that communicate with the Google Ads MCP server (described in detail in the next section).

**Metrics collected:** Impressions, clicks, click-through rate (CTR), average cost-per-click (CPC), total spend, and conversions — at both campaign level and keyword level. All monetary values are converted from Google's internal micros representation to USD.

**Time window:** Always queries `LAST_7_DAYS` to align with the weekly report cycle.

**Output written to CampaignContext:** `performance_data` — the full metrics set plus the top 3 and bottom 3 keywords by CTR.

**Important design note:** MonitorAgent is the only agent that uses the MCP server. All other agents that interact with Google Ads use the Python SDK directly. This separation is intentional: MCP is used for reads, the SDK is used for writes.

---

### 7. Optimize Agent

**Role:** Google Ads Bid and Budget Optimizer

**Responsibility:** Act on the performance data to improve campaign efficiency by making targeted, conservative changes.

**Tools:** `update_keyword_bid`, `pause_keyword`, and `reallocate_budget` — Google Ads SDK write tools.

**Decision rules:**
- Pause keywords with CTR below 1% after 100 or more impressions (wasting budget with no engagement).
- Increase bids by 10–20% on keywords with CTR above 5% and at least one conversion (high performers that could win more impressions).
- Adjust the campaign's daily budget if spend is consistently underpacing or overpacing against the monthly target.

**Fault tolerance:** Each tool call is independent. If one fails, the agent logs the error and continues with the remaining optimisations. A single failed change does not stop the cycle.

**Output written to CampaignContext:** `optimizations` — a list of every change made, including the before and after values, for inclusion in the weekly report.

---

### 8. Report Agent

**Role:** Campaign Reporting Analyst

**Responsibility:** Write a concise, plain-English weekly performance summary for the business owner.

**Tools:** None. Pure LLM agent with `use_system_prompt=False`.

**Output format:** 150–250 words. Opens with the biggest win of the week. Explains what was optimised and why. Closes with one concrete recommendation for the coming week. No jargon — every metric is translated into terms a non-technical business owner can understand.

**Output written to CampaignContext:** `weekly_report` — the plain-text summary string.

---

## How Agents Communicate — The Campaign Context

All eight agents share a single `CampaignContext` object. It is defined in `backend/core/campaign_context.py` as a Pydantic model.

```
CampaignContext
├── campaign_id            (UUID — generated at POST /campaigns)
├── business_description   (user input)
├── monthly_budget         (user input — USD)
├── geo_targets            (user input — list of location strings)
├── campaign_status        (PENDING / RUNNING / DONE / FAILED)
│
├── business_profile       (written by ResearchAgent)
├── keyword_strategy       (written by KeywordAgent)
├── ad_creatives           (written by CreativeAgent)
├── qa_result              (written by QAAgent)
├── campaign_ids           (written by LaunchAgent)
├── performance_data       (written by MonitorAgent)
├── optimizations          (written by OptimizeAgent)
├── weekly_report          (written by ReportAgent)
│
└── agent_states           (per-agent: status, timestamps, logs, output)
    ├── ResearchAgent      (IDLE / RUNNING / DONE / FAILED)
    ├── KeywordAgent
    ├── CreativeAgent
    ├── QAAgent
    ├── LaunchAgent
    ├── MonitorAgent
    ├── OptimizeAgent
    └── ReportAgent
```

The context is serialised to JSON and stored in Redis after every agent step. If the server restarts mid-pipeline, the context is retrieved from Redis and no work is lost. The Redis TTL is set to 7 days by default.

The orchestration logic in `backend/core/crew.py` uses CrewAI's `step_callback` (`on_step`) to intercept each completed task, parse the agent's output, write it to the appropriate field on the context, update the agent's status, and save the context to Redis.

---

## Google Ads Integration — Two Distinct Mechanisms

AdPilot uses two completely separate mechanisms to interact with the Google Ads platform, each chosen for a specific purpose:

### Mechanism 1 — Google Ads Python SDK (Writes)

Used by: LaunchAgent, OptimizeAgent, and the keyword estimation tool.

The Python SDK (`google-ads==29.2.0`) is the standard client library for making authenticated API calls to the Google Ads REST/gRPC endpoints. It is used for all write operations:

- Creating campaigns, campaign budgets, ad groups, and ads.
- Updating keyword CPC bids.
- Pausing keywords.
- Updating campaign daily budgets.

**Authentication:** OAuth2 with a refresh token. The credentials are set via five environment variables: `GOOGLE_ADS_DEVELOPER_TOKEN`, `GOOGLE_ADS_CLIENT_ID`, `GOOGLE_ADS_CLIENT_SECRET`, `GOOGLE_ADS_REFRESH_TOKEN`, and `GOOGLE_ADS_CUSTOMER_ID`.

**Money representation:** The Google Ads API stores all monetary values in micros (1 USD = 1,000,000 micros). The SDK tools handle the conversion transparently — all public interfaces accept and return USD values.

### Mechanism 2 — Google Ads MCP Server (Reads)

Used by: MonitorAgent only.

The MCP server is used exclusively for read operations — querying live campaign performance data using GAQL. See the dedicated section below for full details.

---

## The Google Ads MCP Server

### What MCP Is

The Model Context Protocol (MCP) is an open standard that defines how AI models and agents communicate with external tools and data sources. An MCP server exposes a set of typed tools that a client (in this case, a CrewAI agent) can call by name with structured arguments.

The official Google Ads MCP server (`google-ads-mcp`) is published by Google and provides a standardised interface for querying the Google Ads API. It communicates over standard input/output (`stdio`) and runs as a local subprocess.

### Why MCP Was Chosen for Monitoring

The monitoring use case is read-only and query-driven. The agent needs to ask: "Give me the impressions, clicks, CTR, CPC, spend, and conversions for this campaign over the last 7 days." GAQL (Google Ads Query Language) is the natural way to express that, and the MCP server's `search` tool accepts structured GAQL query parts directly. This is cleaner than constructing raw GAQL strings in the agent and calling the SDK manually.

Using the MCP server also makes the integration more maintainable: the MCP server handles authentication, query parsing, and response formatting. The agent simply calls a named tool with structured arguments and receives structured results.

### How the MCP Server Runs

The MCP server is installed in an isolated Python virtual environment at `backend/.mcp-runtime/`. The setup script at `backend/scripts/setup_mcp_runtime.sh` creates the virtual environment and installs `google-ads-mcp`:

```bash
bash backend/scripts/setup_mcp_runtime.sh
```

At runtime, the server is launched as a subprocess each time a tool call is made. The launch mechanism in `backend/tools/google_ads_mcp_reader.py` resolves the command in the following priority order:

1. The `GOOGLE_ADS_MCP_COMMAND` environment variable (explicit override).
2. The binary at `backend/.mcp-runtime/bin/google-ads-mcp` (isolated runtime).
3. The `google-ads-mcp` binary on the system `PATH` (fallback).

### Authentication for the MCP Server

The MCP server uses Application Default Credentials (ADC), not the same OAuth client credentials used by the SDK. The credential file is a standard Google ADC JSON file — either a service account key or an authorised user credential generated by `gcloud auth application-default login`. The path to this file is set via `GOOGLE_APPLICATION_CREDENTIALS`.

The system validates the ADC file on every tool call before launching the subprocess. It checks that the file exists, is valid JSON, and has a recognised `type` field (`authorized_user`, `service_account`, etc.). This validation produces a clear, actionable error message rather than a cryptic subprocess failure.

### The Two MCP Tools

**`google_ads_mcp_list_accessible_customers`**

Lists all Google Ads customer IDs accessible to the configured credentials. MonitorAgent calls this first to confirm which customer ID to query before running performance queries.

**`google_ads_mcp_search`**

Runs a GAQL query and returns performance data. The tool accepts structured query parts rather than a raw GAQL string:

| Argument | Type | Description |
|---|---|---|
| `customer_id` | string | Google Ads account digits only (e.g. `1234567890`) |
| `fields_csv` | string | Comma-separated fields (e.g. `campaign.id,metrics.clicks,metrics.ctr`) |
| `resource` | string | GAQL resource name (e.g. `campaign`, `keyword_view`) |
| `conditions_csv` | string | Optional comma-separated filter clauses |
| `orderings_csv` | string | Optional comma-separated order clauses |
| `limit` | integer | Maximum rows to return (default: 100) |

An example invocation for a campaign-level weekly performance query:

```
resource:    campaign
fields_csv:  campaign.id, metrics.impressions, metrics.clicks,
             metrics.ctr, metrics.average_cpc, metrics.cost_micros,
             metrics.conversions
conditions_csv: segments.date DURING LAST_7_DAYS
limit: 100
```

The MCP server translates these parts into the equivalent GAQL statement, executes it against the Google Ads API, and returns the results as JSON.

### The stdio Communication Flow

Each tool call goes through the following sequence:

1. The tool function in `google_ads_mcp_reader.py` constructs the argument payload.
2. `_call_mcp_tool_async` opens a stdio client connection to the MCP subprocess using the `mcp` Python library.
3. The MCP client initialises the session and calls the named tool with the argument payload.
4. The MCP server executes the GAQL query against the Google Ads API using ADC authentication.
5. The result is returned through the stdio channel and serialised to a JSON string.
6. The JSON string is returned to CrewAI as the tool's output, which the agent reads as part of its reasoning.

The MCP subprocess is short-lived — it starts on each tool call and exits when the session closes. This avoids managing a persistent subprocess lifecycle.

---

## Real-Time Pipeline Updates — WebSocket and Event Bus

The backend publishes live agent status updates to connected browser clients over WebSocket.

### Event Bus

`backend/core/event_bus.py` implements a lightweight in-memory pub/sub system. It maintains one `asyncio.Queue` per campaign per connected browser tab. When `crew.py`'s `on_step` callback fires after an agent completes, it calls `event_bus.publish()`, which pushes a `PipelineEvent` onto every queue subscribed to that campaign ID.

### WebSocket Endpoint

`GET /live/{campaign_id}` (WebSocket upgrade) handles the browser connection:

1. On connect, it immediately sends a `catch_up` message containing the current state of all agents from Redis. This ensures a late-joining client (one that connects after some agents have already finished) gets the full picture immediately.
2. It subscribes to the event bus and enters a loop, reading events from the queue and sending them as JSON messages to the browser.
3. When the pipeline finishes, `crew.py` calls `event_bus.publish_done()`, which puts a `None` sentinel into every queue. The WebSocket handler sends a `pipeline_done` message and closes cleanly.
4. On client disconnect, the queue is unsubscribed and removed to prevent memory leaks.

### Message Types

| Type | When sent | Contents |
|---|---|---|
| `catch_up` | Immediately on connect | All agent states from Redis |
| `agent_update` | After each agent completes | Agent name, status, output, log entry |
| `pipeline_done` | When all 8 agents finish | Campaign ID |

---

## Backend Technology Stack

| Component | Technology | Version | Purpose |
|---|---|---|---|
| Web framework | FastAPI | 0.115.5 | REST API and WebSocket server |
| ASGI server | Uvicorn | 0.32.1 | Production-grade async server |
| Agent orchestration | CrewAI | 0.80.0 | Multi-agent pipeline |
| LLM inference | Ollama (gemma3:4b) | local | All LLM reasoning tasks |
| LLM client | LiteLLM | 1.52.9 | Unified LLM interface for CrewAI |
| Google Ads SDK | google-ads | 29.2.0 | Write operations (campaigns, ads, bids) |
| MCP client | mcp (Python library) | — | Communication with Google Ads MCP server |
| State persistence | Redis | — | Campaign context storage and TTL management |
| Scheduler | APScheduler | 3.10.4 | Post-launch maintenance jobs |
| Web scraping | httpx + BeautifulSoup4 | — | Research agent scraping |
| Data validation | Pydantic v2 | 2.10.2 | Campaign context schema and settings |
| Retry logic | Tenacity | 9.0.0 | Resilient API calls |

---

## Frontend Technology Stack

| Component | Technology | Purpose |
|---|---|---|
| UI framework | React 19 | Component rendering |
| Language | TypeScript | Type-safe frontend code |
| Build tool | Vite 8 | Fast development server and bundler |
| State management | Redux Toolkit | Campaign and agent state |
| Routing | React Router v7 | Page navigation |
| Charts | Recharts | Performance visualisations (budget gauge, performance chart) |
| Real-time | Native WebSocket API | Live agent pipeline updates |

### Frontend Pages

- **Home** — list of all campaigns stored in Redis.
- **New Campaign** — form to submit a new campaign (business description, budget, geo targets).
- **Campaign Detail** — live pipeline view showing each agent's status, logs, and structured output.
- **Reports** — weekly report display for a completed campaign.

---

## API Reference

### Campaigns

| Method | Path | Description |
|---|---|---|
| POST | `/campaigns` | Start a new campaign pipeline. Returns `campaign_id` immediately (HTTP 202). |
| GET | `/campaigns` | List all campaign IDs stored in Redis. |
| GET | `/campaigns/{campaign_id}` | Full campaign context including all agent outputs. |
| GET | `/campaigns/{campaign_id}/status` | Lightweight status endpoint — agent states only, no full output. |

### Reports

| Method | Path | Description |
|---|---|---|
| GET | `/reports/{campaign_id}` | The plain-English weekly report for a completed campaign. |

### WebSocket

| Protocol | Path | Description |
|---|---|---|
| WebSocket | `/live/{campaign_id}` | Live agent event stream for a running campaign. |

### Health

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Returns application name, version, and Ollama model name. |

---

## Project Structure

```
Albus-Dumbledore/
├── backend/
│   ├── agents/
│   │   ├── base_agent.py           # Shared agent factory with LLM + prompt loading
│   │   ├── research_agent.py
│   │   ├── keyword_agent.py
│   │   ├── creative_agent.py
│   │   ├── qa_agent.py
│   │   ├── launch_agent.py
│   │   ├── monitor_agent.py
│   │   ├── optimize_agent.py
│   │   └── report_agent.py
│   ├── api/
│   │   ├── campaigns.py            # REST endpoints for campaign CRUD
│   │   ├── reports.py              # Report retrieval endpoint
│   │   └── ws.py                   # WebSocket live event stream
│   ├── core/
│   │   ├── campaign_context.py     # Shared Pydantic state object
│   │   ├── crew.py                 # CrewAI orchestration — builds and runs the pipeline
│   │   ├── event_bus.py            # In-memory asyncio pub/sub for WebSocket events
│   │   ├── scheduler.py            # APScheduler for post-launch maintenance jobs
│   │   └── tasks.py                # CrewAI task definitions — one per agent
│   ├── models/
│   │   ├── agent_run.py            # AgentRunState, PipelineEvent, AgentLog models
│   │   └── campaign.py             # Campaign, CampaignCreateRequest/Response models
│   ├── prompts/
│   │   ├── research.txt            # System prompt for ResearchAgent
│   │   ├── creative.txt            # System prompt for CreativeAgent
│   │   ├── qa_policy.txt           # Policy rules for QAAgent
│   │   └── report.txt              # Writing guidelines for ReportAgent
│   ├── scripts/
│   │   └── setup_mcp_runtime.sh    # Installs google-ads-mcp in isolated venv
│   ├── services/
│   │   ├── google_ads_client.py    # GoogleAdsClient singleton for SDK tools
│   │   ├── llm_client.py           # Ollama LLM setup and health check
│   │   └── redis_store.py          # Redis read/write helpers for CampaignContext
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_api.py
│   │   ├── test_crew.py
│   │   ├── test_tools.py
│   │   ├── test_full_agent_flow.py
│   │   ├── test_google_ads_live.py
│   │   ├── test_ollama_agent_responses.py
│   │   ├── test_real_external_stack.py
│   │   └── test_actual_response.py
│   ├── tools/
│   │   ├── google_ads_mcp_reader.py   # MCP bridge tools for MonitorAgent
│   │   ├── google_ads_sdk_tools.py    # SDK write tools for Launch and Optimize agents
│   │   └── scraper_tools.py           # Web scraping tools for ResearchAgent
│   ├── config.py                   # Pydantic settings with .env loading
│   ├── main.py                     # FastAPI app, startup/shutdown, router registration
│   ├── oauth.py                    # OAuth helpers for Google credential flows
│   ├── Dockerfile
│   └── requirements.txt
│
└── frontend/
    ├── src/
    │   ├── components/
    │   │   ├── agents/             # AgentCard, AgentLog, AgentPipeline
    │   │   ├── campaign/           # CampaignCard, CampaignForm, StatusBadge
    │   │   ├── charts/             # BudgetGauge, PerformanceChart (Recharts)
    │   │   ├── layout/             # Sidebar, TopNav
    │   │   └── ui/                 # Button, Input, Modal, Spinner, Toast
    │   ├── hooks/
    │   │   ├── useAgentStatus.ts
    │   │   ├── useCampaign.ts
    │   │   └── useWebSocket.ts     # WebSocket hook for live pipeline updates
    │   ├── pages/
    │   │   ├── Home.tsx
    │   │   ├── NewCampaign.tsx
    │   │   ├── CampaignDetail.tsx
    │   │   └── Reports.tsx
    │   ├── services/
    │   │   ├── api.ts              # REST API client functions
    │   │   └── websocket.ts        # WebSocket connection manager
    │   ├── store/
    │   │   ├── index.ts            # Redux store configuration
    │   │   ├── agentSlice.ts       # Agent state slice
    │   │   └── campaignSlice.ts    # Campaign state slice
    │   └── types/
    │       ├── agent.ts
    │       ├── api.ts
    │       └── campaign.ts
    ├── package.json
    └── vite.config.ts
```

---

## Prerequisites

- Python 3.10 or higher
- Node.js 18 or higher (for the frontend)
- [Ollama](https://ollama.com) installed and running locally
- Redis running locally or accessible via URL
- A Google Ads account with an approved developer token
- A Google Cloud project with the Google Ads API enabled
- Application Default Credentials (ADC) JSON file for the MCP server

---

## Installation and Setup

### 1. Clone the repository

```bash
git clone https://github.com/saaj376/Albus-Dumbledore.git
cd Albus-Dumbledore
```

### 2. Pull the Ollama model

```bash
ollama pull gemma3:4b
```

### 3. Install backend dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 4. Install the Google Ads MCP server in an isolated runtime

```bash
bash scripts/setup_mcp_runtime.sh
```

This creates a virtual environment at `backend/.mcp-runtime/` and installs `google-ads-mcp` into it. The MCP reader tool will find it automatically.

### 5. Configure environment variables

Copy the example and fill in your credentials:

```bash
cp .env.example .env
```

See the Environment Variables section below for all required values.

### 6. Install frontend dependencies

```bash
cd ../frontend
npm install
```

---

## Environment Variables

All variables are loaded from `backend/.env`. The settings are defined in `backend/config.py`.

### Application

| Variable | Default | Description |
|---|---|---|
| `APP_NAME` | `AdPilot` | Application name shown in the health endpoint |
| `APP_VERSION` | `0.1.0` | Application version |
| `DEBUG` | `false` | Enable FastAPI debug mode |

### Ollama (LLM)

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | URL where Ollama is running |
| `OLLAMA_MODEL` | `gemma3:4b` | Model to use for all agent reasoning |

### Redis

| Variable | Default | Description |
|---|---|---|
| `REDIS_URL` | `redis://localhost:6379` | Redis connection URL |
| `REDIS_TTL_SECONDS` | `604800` | Campaign context TTL (7 days) |

### Google Ads SDK (Writes — LaunchAgent, OptimizeAgent)

| Variable | Description |
|---|---|
| `GOOGLE_ADS_DEVELOPER_TOKEN` | Your Google Ads developer token |
| `GOOGLE_ADS_CLIENT_ID` | OAuth2 client ID from Google Cloud Console |
| `GOOGLE_ADS_CLIENT_SECRET` | OAuth2 client secret |
| `GOOGLE_ADS_REFRESH_TOKEN` | OAuth2 refresh token for the account |
| `GOOGLE_ADS_CUSTOMER_ID` | Your Google Ads customer ID (digits only) |

### Google Ads MCP Server (Reads — MonitorAgent)

| Variable | Description |
|---|---|
| `GOOGLE_APPLICATION_CREDENTIALS` | Absolute path to your ADC credentials JSON file |
| `GOOGLE_PROJECT_ID` | Your Google Cloud project ID (e.g. `adpilot-490718`) |

The ADC credential file must be of type `authorized_user` or `service_account`. It is the file produced by `gcloud auth application-default login`, not an OAuth client secrets file downloaded from the API credentials page.

---

## Running the Application

### Start the backend

```bash
cd backend
uvicorn main:app --reload --port 8000
```

On startup, the application checks that Ollama is running and the configured model is available. If either check fails, the server will not start and a descriptive error is printed.

### Start the frontend

```bash
cd frontend
npm run dev
```

The Vite development server starts on `http://localhost:5173` by default. The backend must be running on port 8000 for API calls to succeed.

### Start a campaign

Send a POST request to the backend (or use the New Campaign page in the frontend):

```bash
curl -X POST http://localhost:8000/campaigns \
  -H "Content-Type: application/json" \
  -d '{
    "business_description": "A family-owned Italian restaurant in Austin, TX specialising in wood-fired Neapolitan pizza.",
    "monthly_budget": 1500.0,
    "geo_targets": ["Austin, TX"]
  }'
```

The response includes a `campaign_id`. Connect to `ws://localhost:8000/live/{campaign_id}` to receive live agent updates, or open the Campaign Detail page in the frontend.

---

## License

[MIT](LICENSE)
