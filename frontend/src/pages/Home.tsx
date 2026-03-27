import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { TopNav } from '../components/layout/TopNav'
import { CampaignCard } from '../components/campaign/CampaignCard'
import { getCampaign, getCampaignIds, getCampaignStatus } from '../services/api'
import type { CampaignSummary } from '../types/campaign'

function toBusinessName(context: { business_profile: Record<string, unknown>; business_description: string }): string {
	const raw = context.business_profile.business_name
	if (typeof raw === 'string' && raw.trim().length > 0) {
		return raw.trim()
	}
	return context.business_description.split('.').at(0)?.trim() || 'Untitled campaign'
}

function toSpend(performanceData: Record<string, unknown>): number {
	const candidates = [
		performanceData.spend,
		performanceData.total_spend,
		performanceData.cost,
		performanceData.spend_usd,
	]

	for (const candidate of candidates) {
		if (typeof candidate === 'number' && Number.isFinite(candidate)) {
			return candidate
		}
	}
	return 0
}

function formatCurrency(value: number): string {
	return new Intl.NumberFormat('en-US', {
		style: 'currency',
		currency: 'USD',
		maximumFractionDigits: 0,
	}).format(value)
}

export function HomePage() {
	const [campaigns, setCampaigns] = useState<CampaignSummary[]>([])
	const [loading, setLoading] = useState(true)
	const [error, setError] = useState<string | null>(null)

	useEffect(() => {
		let cancelled = false

		async function load(): Promise<void> {
			setLoading(true)
			setError(null)
			try {
				const list = await getCampaignIds()
				const summaries = await Promise.all(
					list.campaign_ids.map(async (id) => {
						const [context, status] = await Promise.all([getCampaign(id), getCampaignStatus(id)])
						return {
							id,
							businessName: toBusinessName(context),
							status: status.campaign_status,
							monthlyBudget: context.monthly_budget,
							createdAt: context.created_at,
							totalSpend: toSpend(context.performance_data),
						} satisfies CampaignSummary
					}),
				)

				if (!cancelled) {
					const sorted = summaries.sort((a, b) => b.createdAt.localeCompare(a.createdAt))
					setCampaigns(sorted)
				}
			} catch {
				if (!cancelled) {
					setError('Failed to load campaigns. Make sure backend is running on port 8000.')
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

	const quickStats = useMemo(() => {
		const totalCampaigns = campaigns.length
		const activeCampaigns = campaigns.filter((campaign) =>
			['PENDING', 'RUNNING', 'LAUNCHED'].includes(campaign.status),
		).length
		const totalSpend = campaigns.reduce((sum, campaign) => sum + campaign.totalSpend, 0)

		return { totalCampaigns, activeCampaigns, totalSpend }
	}, [campaigns])

	return (
		<div className="page-shell">
			<TopNav
				title="Campaign List Dashboard"
				subtitle="All campaigns at a glance"
				actions={
					<Link to="/campaigns/new" className="primary-btn">
						New Campaign
					</Link>
				}
			/>

			<section className="stats-grid">
				<article className="stat-card">
					<h4>Total Campaigns</h4>
					<strong>{quickStats.totalCampaigns}</strong>
				</article>
				<article className="stat-card">
					<h4>Active Campaigns</h4>
					<strong>{quickStats.activeCampaigns}</strong>
				</article>
				<article className="stat-card">
					<h4>Total Spend</h4>
					<strong>{formatCurrency(quickStats.totalSpend)}</strong>
				</article>
			</section>

			{loading ? <p className="empty-state">Loading campaigns...</p> : null}
			{error ? <p className="form-error">{error}</p> : null}

			{!loading && !error && campaigns.length === 0 ? (
				<p className="empty-state">No campaigns yet. Create your first one.</p>
			) : null}

			<section className="campaign-list-grid">
				{campaigns.map((campaign) => (
					<CampaignCard key={campaign.id} campaign={campaign} />
				))}
			</section>
		</div>
	)
}

