import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { TopNav } from '../components/layout/TopNav'
import { getCampaignIds, getReport, isApiError } from '../services/api'
import type { ReportResponse } from '../types/api'

interface ReportCardData {
	report: ReportResponse
	impressions: number
	clicks: number
	costPerVisit: number
	topSearchTerm: string
}

function asNumber(record: Record<string, unknown>, key: string): number {
	const value = record[key]
	return typeof value === 'number' && Number.isFinite(value) ? value : 0
}

function buildReportCard(report: ReportResponse): ReportCardData {
	const metrics = report.performance_data
	const impressions = asNumber(metrics, 'impressions')
	const clicks = asNumber(metrics, 'clicks')
	const spend = asNumber(metrics, 'spend') || asNumber(metrics, 'total_spend') || asNumber(metrics, 'cost')
	const term =
		(report.optimizations.top_search_term as string | undefined) ||
		(metrics.top_search_term as string | undefined) ||
		'Not available yet'

	return {
		report,
		impressions,
		clicks,
		costPerVisit: clicks > 0 ? spend / clicks : 0,
		topSearchTerm: term,
	}
}

function formatCurrency(value: number): string {
	return new Intl.NumberFormat('en-US', {
		style: 'currency',
		currency: 'USD',
		maximumFractionDigits: 2,
	}).format(value)
}

export function ReportsPage() {
	const [cards, setCards] = useState<ReportCardData[]>([])
	const [expandedId, setExpandedId] = useState<string | null>(null)
	const [loading, setLoading] = useState(true)
	const [error, setError] = useState<string | null>(null)

	useEffect(() => {
		let cancelled = false

		async function load(): Promise<void> {
			setLoading(true)
			setError(null)
			try {
				const list = await getCampaignIds()
				const reports = await Promise.all(
					list.campaign_ids.map(async (campaignId) => {
						try {
							const report = await getReport(campaignId)
							return buildReportCard(report)
						} catch (loadError) {
							if (isApiError(loadError) && (loadError.status === 404 || loadError.status === 425)) {
								return null
							}
							throw loadError
						}
					}),
				)

				if (!cancelled) {
					const available = reports.filter((item): item is ReportCardData => item !== null)
					available.sort((a, b) => b.report.created_at.localeCompare(a.report.created_at))
					setCards(available)
				}
			} catch {
				if (!cancelled) {
					setError('Failed to load reports.')
				}
			} finally {
				if (!cancelled) {
					setLoading(false)
				}
			}
		}

		void load()
		return () => {
			cancelled = true
		}
	}, [])

	const pageTotal = useMemo(() => cards.length, [cards])

	return (
		<div className="page-shell">
			<TopNav title="Weekly Reports" subtitle={`Plain-English summaries for completed campaigns (${pageTotal})`} />

			{loading ? <p className="empty-state">Loading reports...</p> : null}
			{error ? <p className="form-error">{error}</p> : null}

			{!loading && !error && cards.length === 0 ? (
				<p className="empty-state">No completed campaign reports available yet.</p>
			) : null}

			<section className="reports-list">
				{cards.map((card) => {
					const isExpanded = expandedId === card.report.campaign_id
					const preview = card.report.weekly_report.split('\n').at(0) ?? card.report.weekly_report

					return (
						<article key={card.report.campaign_id} className="report-card">
							<div className="report-head">
								<h3>{card.report.business_name || card.report.campaign_id}</h3>
								<button
									type="button"
									className="ghost-btn"
									onClick={() =>
										setExpandedId((prev) => (prev === card.report.campaign_id ? null : card.report.campaign_id))
									}
								>
									{isExpanded ? 'Collapse' : 'Expand'}
								</button>
							</div>

							<p>{isExpanded ? card.report.weekly_report : preview}</p>

							<div className="report-metrics">
								<span>People reached: {card.impressions.toLocaleString('en-US')}</span>
								<span>Website visits: {card.clicks.toLocaleString('en-US')}</span>
								<span>Cost per visit: {formatCurrency(card.costPerVisit)}</span>
								<span>Top search term: {card.topSearchTerm}</span>
							</div>

							<Link to={`/campaigns/${card.report.campaign_id}`} className="campaign-link">
								View Campaign
							</Link>
						</article>
					)
				})}
			</section>
		</div>
	)
}

