import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { TopNav } from '../components/layout/TopNav'
import { getCampaignIds, getReport, isApiError } from '../services/api'
import type { ReportResponse } from '../types/api'

interface ReportCardData { report: ReportResponse }
function buildReportCard(report: ReportResponse): ReportCardData { return { report } }

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
			<TopNav title="Campaign Plan Summaries" subtitle={`Plain-English summaries for completed plans (${pageTotal})`} />

			{loading ? <p className="empty-state">Loading reports...</p> : null}
			{error ? <p className="form-error">{error}</p> : null}

			{!loading && !error && cards.length === 0 ? (
				<p className="empty-state">No completed campaign plans available yet.</p>
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

