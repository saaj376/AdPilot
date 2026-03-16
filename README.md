# 🤖 Albus Dumbledore — Multi-Agent Autonomous Campaign Lifecycle Manager

> A proof-of-concept for how agentic AI could eliminate SMB advertiser churn on Google Ads.

---

## 🧠 The Problem

Small businesses abandon Google Ads — not because the platform doesn't work, but because **it's too complex to manage**.

From keyword research and ad copywriting to bid optimization and performance monitoring, the operational burden is enormous for a team of one. Google has been trying to simplify Ads for SMBs for years. This solves it elegantly with AI.

---

## 💡 The Solution

A fully autonomous, multi-agent system that takes a **single business description as input** and handles the entire Google Ads campaign lifecycle — research, build, launch, monitor, and optimize — with **zero manual intervention**.

---

## 🏗️ Architecture Overview

```
Business Description (Input)
         │
         ▼
┌─────────────────┐
│  Research Agent │  ── Scrapes web, understands business, maps competitors
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Keyword Agent  │  ── Calls Google Keyword Planner API, builds keyword strategy
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Creative Agent  │  ── Writes headlines, descriptions, CTAs tailored to audience
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    QA Agent     │  ── Reviews copy against Google Ads policies before launch
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Launch Agent   │  ── Creates campaign structure via Google Ads API
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Monitor Agent   │  ── Watches live performance, detects anomalies
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Optimize Agent  │  ── Adjusts bids, pauses underperformers, reallocates budget
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Report Agent   │  ── Generates weekly plain-English performance summaries
└─────────────────┘
```

---

## 🤖 The Agents

| Agent | Role | Key Capability |
|---|---|---|
| 🔍 **Research Agent** | Business & market intelligence | Web scraping, competitor mapping, audience profiling |
| 🔑 **Keyword Agent** | Keyword strategy | Google Keyword Planner API integration, intent clustering |
| ✍️ **Creative Agent** | Ad copy generation | Headlines, descriptions, CTAs — tailored by audience segment |
| ✅ **QA Agent** | Policy compliance | Pre-launch review against Google Ads editorial policies |
| 🚀 **Launch Agent** | Campaign deployment | Full campaign structure creation via Google Ads API |
| 📡 **Monitor Agent** | Live performance tracking | Anomaly detection, CTR drops, budget pacing alerts |
| 🔧 **Optimize Agent** | Continuous improvement | Bid adjustments, pausing underperformers, budget reallocation |
| 📊 **Report Agent** | Stakeholder reporting | Weekly plain-English summaries with key insights |

---

## 🔄 How Agents Communicate

Agents operate in a **sequential pipeline with shared state**. Each agent writes its output to a central **Campaign Context Object** that downstream agents read from.

```json
{
  "business_profile":  { },   // Research Agent output
  "keyword_strategy":  { },   // Keyword Agent output
  "ad_creatives":      { },   // Creative Agent output
  "qa_review":         { },   // QA Agent output
  "campaign_ids":      { },   // Launch Agent output
  "performance_data":  { },   // Monitor Agent output
  "optimizations":     { },   // Optimize Agent output
  "weekly_report":     { }    // Report Agent output
}
```

> **Note:** The `Monitor → Optimize → Report` loop runs continuously post-launch for autonomous lifecycle management.

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- Google Ads API credentials
- Google Cloud project with Keyword Planner access

### Installation

```bash
git clone https://github.com/your-org/albus-dumbledore.git
cd albus-dumbledore
pip install -r requirements.txt
cp .env.example .env  # Add your API keys
```

### Run

```bash
python main.py --business "A family-owned Italian restaurant in Austin, TX specializing in wood-fired pizza."
```

---

## 📁 Project Structure

```
albus-dumbledore/
├── agents/
│   ├── research_agent.py
│   ├── keyword_agent.py
│   ├── creative_agent.py
│   ├── qa_agent.py
│   ├── launch_agent.py
│   ├── monitor_agent.py
│   ├── optimize_agent.py
│   └── report_agent.py
├── core/
│   ├── campaign_context.py   # Shared state object
│   ├── pipeline.py           # Agent orchestration
│   └── config.py
├── main.py
├── requirements.txt
└── README.md
```
---

## 🤝 Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you'd like to change.

---

## 📄 License

[MIT](LICENSE)
