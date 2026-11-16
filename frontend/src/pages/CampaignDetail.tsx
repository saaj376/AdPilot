import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { useParams } from 'react-router-dom'
import { AgentLog } from '../components/agents/AgentLog'
import { AgentPipeline } from '../components/agents/AgentPipeline'
import { StatusBadge } from '../components/campaign/StatusBadge'
import { BudgetGauge } from '../components/charts/BudgetGauge'
import { PerformanceChart, type PerformancePoint } from '../components/charts/PerformanceChart'
import { TopNav } from '../components/layout/TopNav'
import { getCampaign } from '../services/api'
import { connectCampaignWebSocket } from '../services/websocket'
import type { AgentRunState, CampaignWsMessage } from '../types/agent'
import type { CampaignContext } from '../types/campaign'

const ORDERED_AGENT_NAMES = [
	'ResearchAgent',
	'KeywordAgent',
	'CreativeAgent',
	'QAAgent',
	'LaunchAgent',
	'MonitorAgent',
	'OptimizeAgent',
	'ReportAgent',
]

const AGENT_FIELD_MAP: Record<string, keyof CampaignContext> = {
	ResearchAgent: 'business_profile',
	KeywordAgent: 'keyword_strategy',
	CreativeAgent: 'ad_creatives',
	QAAgent: 'qa_result',
	LaunchAgent: 'campaign_ids',
	MonitorAgent: 'performance_data',
	OptimizeAgent: 'optimizations',
	ReportAgent: 'weekly_report',
}

function formatLogLine(agentName: string, timestamp: string, message: string): string {
	const time = new Date(timestamp).toLocaleTimeString('en-US', {
		hour12: false,
		hour: '2-digit',
		minute: '2-digit',
		second: '2-digit',
	})
	return `[${time}] ${agentName}: ${message}`
}

function toMetric(performanceData: Record<string, unknown>, key: string): number {
	const value = performanceData[key]
	return typeof value === 'number' && Number.isFinite(value) ? value : 0
}

function extractSeries(performanceData: Record<string, unknown>): PerformancePoint[] {
	const history = performanceData.history
	if (Array.isArray(history)) {
		const mapped = history
			.map((row, index) => {
				if (!row || typeof row !== 'object') {
					return null
				}
				const safe = row as Record<string, unknown>
				return {
					label: typeof safe.label === 'string' ? safe.label : `T${index + 1}`,
					ctr: typeof safe.ctr === 'number' ? safe.ctr : 0,
					cpc: typeof safe.cpc === 'number' ? safe.cpc : 0,
				}
			})
			.filter((row): row is PerformancePoint => row !== null)

		if (mapped.length > 0) {
			return mapped
		}
	}

	return [
		{
			label: 'Now',
			ctr: toMetric(performanceData, 'ctr'),
			cpc: toMetric(performanceData, 'cpc'),
		},
	]
}

function makeDefaultAgentStates(): Record<string, AgentRunState> {
	const states: Record<string, AgentRunState> = {}
	for (const name of ORDERED_AGENT_NAMES) {
		states[name] = {
			status: 'IDLE',
			started_at: null,
			finished_at: null,
			logs: [],
		}
	}
	return states
}

function pickActiveAgent(agentStates: Record<string, AgentRunState>): string {
	const running = ORDERED_AGENT_NAMES.find((name) => agentStates[name]?.status === 'RUNNING')
	if (running) {
		return running
	}

	const completed = [...ORDERED_AGENT_NAMES].reverse().find((name) => agentStates[name]?.status === 'DONE')
	if (completed) {
		return completed
	}

	return ORDERED_AGENT_NAMES[0]
}

function parseMaybeJson(text: string): string {
	try {
		const parsed = JSON.parse(text)
		return JSON.stringify(parsed, null, 2)
	} catch {
		return text
	}
}

function humanizeKey(key: string): string {
	return key
		.replace(/_/g, ' ')
		.replace(/([a-z])([A-Z])/g, '$1 $2')
		.replace(/\b\w/g, (char) => char.toUpperCase())
}

function normalizePayload(payload: unknown): unknown {
	if (payload === null || payload === undefined) {
		return null
	}

	if (typeof payload === 'string') {
		const maybeJson = parseMaybeJson(payload)
		if (maybeJson !== payload) {
			try {
				return JSON.parse(maybeJson)
			} catch {
				return maybeJson
			}
		}
		return payload
	}

	return payload
}

function isMeaningfulText(value: string): boolean {
	const cleaned = value.trim()
	if (!cleaned) {
		return false
	}

	const lowered = cleaned.toLowerCase()
	if (['true', 'false', 'null', 'undefined', 'n/a', 'na', '{}', '[]'].includes(lowered)) {
		return false
	}

	const blockedFragments = [
		'action ',
		'tool name',
		'tool arguments',
		'tool description',
		'i encountered an error',
		'observation:',
		'thought:',
		'final answer:',
	]
	if (blockedFragments.some((fragment) => lowered.includes(fragment))) {
		return false
	}

	if (cleaned.startsWith('{') || cleaned.startsWith('[')) {
		return false
	}

	return /[a-zA-Z]/.test(cleaned) || /\d/.test(cleaned)
}

function splitToPhrases(value: string): string[] {
	return value
		.split(/[\n\r•;|]+|\s{2,}/g)
		.map((chunk) => chunk.trim())
		.filter((chunk) => chunk.length > 0)
}

function uniqLimited(values: string[], limit: number): string[] {
	const result: string[] = []
	const seen = new Set<string>()
	for (const value of values) {
		const key = value.toLowerCase()
		if (seen.has(key)) {
			continue
		}
		seen.add(key)
		result.push(value)
		if (result.length >= limit) {
			break
		}
	}
	return result
}

function collectStrings(value: unknown, bag: string[], depth = 0): void {
	if (depth > 3 || bag.length > 16 || value === null || value === undefined) {
		return
	}

	if (typeof value === 'string') {
		const phrases = splitToPhrases(value)
		for (const phrase of phrases) {
			if (isMeaningfulText(phrase)) {
				bag.push(phrase)
			}
		}
		return
	}

	if (typeof value === 'number') {
		bag.push(String(value))
		return
	}

	if (Array.isArray(value)) {
		for (const item of value) {
			collectStrings(item, bag, depth + 1)
			if (bag.length > 16) {
				break
			}
		}
		return
	}

	if (typeof value === 'object') {
		for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
			// Expanded regex to catch more common Google Ads keys
			if (/keyword|theme|audience|summary|title|name|headline|description|location|benefit|feature|ad_groups|insights/i.test(k) && typeof v === 'string') {
				for (const phrase of splitToPhrases(v)) {
					if (isMeaningfulText(phrase)) {
						bag.push(phrase)
					}
				}
			}
			collectStrings(v, bag, depth + 1)
			if (bag.length > 16) {
				break
			}
		}
	}
}

function collectKeywordChips(value: unknown, bag: string[]): void {
	if (bag.length > 10 || value === null || value === undefined) {
		return
	}

	if (typeof value === 'string') {
		for (const token of value.split(/[\n,|;]+/g)) {
			const cleaned = token.trim()
			if (cleaned.length >= 3 && cleaned.length <= 40 && isMeaningfulText(cleaned)) {
				bag.push(cleaned)
			}
		}
		return
	}

	if (Array.isArray(value)) {
		for (const item of value) {
			if (typeof item === 'string' && /\w/.test(item)) {
				collectKeywordChips(item, bag)
			}
			if (typeof item === 'object' && item && 'text' in item) {
				const text = (item as Record<string, unknown>).text
				if (typeof text === 'string') {
					collectKeywordChips(text, bag)
				}
			}
			if (typeof item === 'object' && item) {
				collectKeywordChips(item, bag)
			}
		}
	}

	if (typeof value === 'object' && value) {
		for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
			if (/keyword|phrase|term|theme|audience|ad_groups|headlines/i.test(k)) {
				collectKeywordChips(v, bag)
			}
		}
	}
}

function renderAgentOutput(
	payload: unknown,
	agentName: string,
	agentStatus: string,
	onViewLogs?: () => void,
): ReactNode {
	const normalized = normalizePayload(payload)

	if (normalized === null) {
		return <p className="agent-value-muted">No output yet for this agent.</p>
	}

	const texts: string[] = []
	collectStrings(normalized, texts)
	const cleanTexts = uniqLimited(texts.filter((item) => isMeaningfulText(item)), 14)

	const keywords: string[] = []
	collectKeywordChips(normalized, keywords)
	const cleanKeywords = uniqLimited(keywords.filter((item) => isMeaningfulText(item)), 8)

	const fallbackLabel = agentName.replace('Agent', '')
	const headline = cleanTexts[0] ?? null
	const secondary = cleanTexts[1] ?? 'Detailed agent output gathered from tools and context.'
	const reasoning = cleanTexts[2] ?? 'The agent is compiling results based on task requirements.'
	const insights = cleanTexts.slice(3, 7)
	const chips = cleanKeywords.length > 0 ? cleanKeywords : cleanTexts.slice(0, 6)

	return (
		<div className="live-output-shell">
			<div className="live-output-topbar">
				<div className="live-output-title-wrap">
					<span className="live-dot" />
					<div>
						<p className="live-kicker">Live {fallbackLabel} Output</p>
						<strong>{humanizeKey(agentStatus)}</strong>
					</div>
				</div>
				<div className="live-output-actions">
					<button className="ghost-btn" type="button" onClick={onViewLogs}>
						View Logs
					</button>
				</div>
			</div>

			<div className="live-output-main-card">
				{headline ? (
					<>
						<h5>{headline.length > 96 ? `${headline.slice(0, 96)}...` : headline}</h5>
						<p>{secondary.length > 140 ? `${secondary.slice(0, 140)}...` : secondary}</p>
						<p className="live-reasoning">{reasoning.length > 160 ? `${reasoning.slice(0, 160)}...` : reasoning}</p>
					</>
				) : (
					<div className="raw-output-box">
						<p className="agent-value-muted mb-2">Heuristic summary unavailable. Showing raw payload:</p>
						<pre className="raw-json-pre">{JSON.stringify(normalized, null, 2)}</pre>
					</div>
				)}
			</div>

			<div className="live-output-subgrid">
				<article className="live-subcard">
					<h6>Top Keywords</h6>
					<div className="agent-chip-wrap">
						{chips.length > 0 ? (
							chips.map((item, idx) => (
								<span className="agent-chip" key={`${item}-${idx}`}>
									{item.length > 32 ? `${item.slice(0, 32)}...` : item}
								</span>
							))
						) : (
							<span className="agent-value-muted">No keywords extracted.</span>
						)}
					</div>
				</article>

				<article className="live-subcard">
					<h6>Key Insights</h6>
					<ul className="live-insights-list">
						{(insights.length > 0 ? insights : [secondary]).map((item, idx) => (
							<li key={`${item}-${idx}`}>{item.length > 72 ? `${item.slice(0, 72)}...` : item}</li>
						))}
					</ul>
				</article>
			</div>

			<div className="live-output-approval">
				<span className="approval-mark">✓</span>
				<p>Latest update for {fallbackLabel} captured successfully.</p>
			</div>
		</div>
	)
}

export function CampaignDetailPage() {
	const { campaignId } = useParams<{ campaignId: string }>()
	const [campaign, setCampaign] = useState<CampaignContext | null>(null)
	const [agentStates, setAgentStates] = useState<Record<string, AgentRunState>>(makeDefaultAgentStates)
	const [selectedAgent, setSelectedAgent] = useState<string>(ORDERED_AGENT_NAMES[0])
	const [logs, setLogs] = useState<string[]>([])
	const [error, setError] = useState<string | null>(null)
	// True once the campaign context has been fetched at least once from REST.
	// Pipeline and output panels render immediately from agentStates (updated by WS)
	// so we don't gate them behind this — only the metrics sidebar needs it.
	const campaignLoadedRef = useRef(false)
	const wsHealthyRef = useRef(false)

	useEffect(() => {
		if (!campaignId) {
			return undefined
		}

		wsHealthyRef.current = false
		campaignLoadedRef.current = false
		const activeCampaignId = campaignId

		let cancelled = false

		async function loadContext(): Promise<void> {
			try {
				const context = await getCampaign(activeCampaignId)
				if (!cancelled) {
					campaignLoadedRef.current = true
					setError(null)
					setCampaign(context)
					setAgentStates((prev) => {
						const next = { ...prev, ...context.agent_states }
						setSelectedAgent((current) => (ORDERED_AGENT_NAMES.includes(current) ? current : pickActiveAgent(next)))
						return next
					})
				}
			} catch {
				if (!cancelled) {
					setError('Failed to load campaign details.')
				}
			}
		}

		void loadContext()

		const pollTimer = window.setInterval(() => {
			if (!wsHealthyRef.current) {
				void loadContext()
			}
		}, 4000)

		const disconnect = connectCampaignWebSocket(
			activeCampaignId,
			(message: CampaignWsMessage) => {
				if (cancelled) return
				setError(null)
				wsHealthyRef.current = true

				if (message.type === 'catch_up') {
					setAgentStates((prev) => {
						const next = { ...prev, ...message.agent_states }
						setSelectedAgent((current) => (ORDERED_AGENT_NAMES.includes(current) ? current : pickActiveAgent(next)))
						return next
					})
					// Bug 4 fix: update campaign_status from catch_up so the badge
					// reflects RUNNING immediately without waiting for the REST fetch.
					setCampaign((prev) =>
						prev ? { ...prev, campaign_status: message.campaign_status as CampaignContext['campaign_status'] } : prev
					)
					const catchUpLogs: string[] = []
					for (const [agentName, state] of Object.entries(message.agent_states)) {
						for (const log of state.logs) {
							catchUpLogs.push(formatLogLine(agentName, log.timestamp, log.message))
						}
					}
					setLogs(catchUpLogs)
					return
				}

				if (message.type === 'agent_update') {
					setAgentStates((prev) => ({
						...prev,
						[message.agent_name]: {
							...(prev[message.agent_name] ?? {
								status: 'IDLE',
								started_at: null,
								finished_at: null,
								logs: [],
							}),
							status: message.status,
							output: message.output ?? prev[message.agent_name]?.output ?? null,
							logs: message.log
								? [...(prev[message.agent_name]?.logs ?? []), message.log]
								: (prev[message.agent_name]?.logs ?? []),
						},
					}))
					setSelectedAgent(message.agent_name)

					// Bug 3 + 4 fix: patch campaign's per-agent output field and
					// campaign_status in-place so selectedOutputPayload and the status
					// badge always show live data, not the stale initial REST snapshot.
					if (message.output !== null && message.output !== undefined) {
						const field = AGENT_FIELD_MAP[message.agent_name] as keyof CampaignContext | undefined
						setCampaign((prev) => {
							if (!prev) return prev
							const patch: Partial<CampaignContext> = { campaign_status: 'RUNNING' }
							if (field) {
								;(patch as Record<string, unknown>)[field] = message.output
							}
							return { ...prev, ...patch }
						})
					}

					const liveLog = message.log
					if (liveLog) {
						setLogs((prev) => [...prev, formatLogLine(message.agent_name, liveLog.timestamp, liveLog.message)])
					}
					return
				}

				if (message.type === 'pipeline_done') {
					setCampaign((prev) => (prev ? { ...prev, campaign_status: message.campaign_status } : prev))
					void loadContext()
				}
			},
			() => {
				wsHealthyRef.current = false
				setError('Live stream disconnected. Trying to continue with latest cached data.')
			},
		)

		return () => {
			cancelled = true
			window.clearInterval(pollTimer)
			disconnect()
		}
	}, [campaignId])

	const performanceData = useMemo(() => campaign?.performance_data ?? {}, [campaign?.performance_data])
	const chartData = useMemo(() => extractSeries(performanceData), [performanceData])
	const totalSpend =
		toMetric(performanceData, 'spend') ||
		toMetric(performanceData, 'total_spend') ||
		toMetric(performanceData, 'cost')

	const impressions = toMetric(performanceData, 'impressions')
	const clicks = toMetric(performanceData, 'clicks')
	const conversions = toMetric(performanceData, 'conversions')

	const selectedOutputPayload = useMemo(() => {
		// Always prefer the live agentStates output (updated by WS agent_update messages).
		// Do NOT gate this on `campaign` — the REST fetch may not have resolved yet,
		// but agentStates.output is populated immediately when the WS event arrives.
		const byState = agentStates[selectedAgent]?.output
		if (byState !== null && byState !== undefined) {
			if (typeof byState !== 'object') {
				return byState
			}

			if (!Array.isArray(byState) && Object.keys(byState as Record<string, unknown>).length === 0) {
				// Empty object — fall through to the durable campaign context field.
			} else {
				return byState
			}
		}

		// Fallback: read from the durable campaign context (needs REST data).
		if (!campaign) {
			return null
		}
		const field = AGENT_FIELD_MAP[selectedAgent]
		if (!field) {
			return null
		}
		return campaign[field]
	}, [agentStates, campaign, selectedAgent])

	const scrollToLogs = useCallback((): void => {
		document.getElementById('campaign-logs')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
	}, [])

	if (!campaignId) {
		return <p className="form-error">Missing campaign id.</p>
	}

	// Bug 2 fix: don't gate the whole page on campaign (REST fetch).
	// agentStates is populated immediately from WS, so the pipeline and
	// output panels can render right away. Only the right-column metrics
	// (budget gauge, performance chart) need the full campaign object.
	return (
		<div className="page-shell">
			<TopNav
				title={`Campaign Detail: ${campaignId}`}
				subtitle="Live multi-agent pipeline updates"
				actions={campaign ? <StatusBadge status={campaign.campaign_status} /> : null}
			/>

			{error ? <p className="form-error">{error}</p> : null}

			<section className="detail-grid">
				<div>
					<AgentPipeline
						orderedAgentNames={ORDERED_AGENT_NAMES}
						agentStates={agentStates}
						selectedAgentName={selectedAgent}
						onSelectAgent={setSelectedAgent}
					/>

					<section className="agent-output-shell">
						<div className="agent-output-head">
							<h4>{selectedAgent.replace('Agent', '')} Output</h4>
							<span>{agentStates[selectedAgent]?.status ?? 'IDLE'}</span>
						</div>
						<div className="agent-output-body">
							{renderAgentOutput(
								selectedOutputPayload,
								selectedAgent,
								agentStates[selectedAgent]?.status ?? 'IDLE',
								scrollToLogs,
							)}
						</div>
					</section>
					<div id="campaign-logs">
						<AgentLog lines={logs} />
					</div>
				</div>

				<div className="detail-right-col">
					{campaign ? (
						<>
							<BudgetGauge spend={totalSpend} monthlyBudget={campaign.monthly_budget} />
							<PerformanceChart data={chartData} />
							<section className="key-metrics">
								<h4>Key Numbers</h4>
								<div className="metrics-grid">
									<article>
										<span>Impressions</span>
										<strong>{impressions.toLocaleString('en-US')}</strong>
									</article>
									<article>
										<span>Clicks</span>
										<strong>{clicks.toLocaleString('en-US')}</strong>
									</article>
									<article>
										<span>Conversions</span>
										<strong>{conversions.toLocaleString('en-US')}</strong>
									</article>
								</div>
							</section>
						</>
					) : (
						<p className="empty-state">Loading metrics...</p>
					)}
				</div>
			</section>
		</div>
	)
}

