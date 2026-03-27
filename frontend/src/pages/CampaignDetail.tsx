import { useEffect, useMemo, useRef, useState } from 'react'
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

export function CampaignDetailPage() {
	const { campaignId } = useParams<{ campaignId: string }>()
	const [campaign, setCampaign] = useState<CampaignContext | null>(null)
	const [agentStates, setAgentStates] = useState<Record<string, AgentRunState>>(makeDefaultAgentStates)
	const [logs, setLogs] = useState<string[]>([])
	const [error, setError] = useState<string | null>(null)
	const wsHealthyRef = useRef(false)

	useEffect(() => {
		if (!campaignId) {
			return undefined
		}

		const activeCampaignId = campaignId

		let cancelled = false

		async function loadContext(): Promise<void> {
			try {
				const context = await getCampaign(activeCampaignId)
				if (!cancelled) {
					setCampaign(context)
					setAgentStates((prev) => ({ ...prev, ...context.agent_states }))
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
				setError(null)
				wsHealthyRef.current = true

				if (message.type === 'catch_up') {
					setAgentStates((prev) => ({ ...prev, ...message.agent_states }))
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
							logs: message.log
								? [...(prev[message.agent_name]?.logs ?? []), message.log]
								: (prev[message.agent_name]?.logs ?? []),
						},
					}))

					const liveLog = message.log
					if (liveLog) {
						setLogs((prev) => [...prev, formatLogLine(message.agent_name, liveLog.timestamp, liveLog.message)])
					}
					return
				}

				if (message.type === 'pipeline_done') {
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

	const performanceData = (campaign?.performance_data ?? {}) as Record<string, unknown>
	const chartData = useMemo(() => extractSeries(performanceData), [performanceData])
	const totalSpend =
		toMetric(performanceData, 'spend') ||
		toMetric(performanceData, 'total_spend') ||
		toMetric(performanceData, 'cost')

	const impressions = toMetric(performanceData, 'impressions')
	const clicks = toMetric(performanceData, 'clicks')
	const conversions = toMetric(performanceData, 'conversions')

	if (!campaignId) {
		return <p className="form-error">Missing campaign id.</p>
	}

	return (
		<div className="page-shell">
			<TopNav
				title={`Campaign Detail: ${campaignId}`}
				subtitle="Live multi-agent pipeline updates"
				actions={campaign ? <StatusBadge status={campaign.campaign_status} /> : null}
			/>

			{error ? <p className="form-error">{error}</p> : null}

			{!campaign ? (
				<p className="empty-state">Loading campaign...</p>
			) : (
				<section className="detail-grid">
					<div>
						<AgentPipeline orderedAgentNames={ORDERED_AGENT_NAMES} agentStates={agentStates} />
						<AgentLog lines={logs} />
					</div>

					<div className="detail-right-col">
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
					</div>
				</section>
			)}
		</div>
	)
}

