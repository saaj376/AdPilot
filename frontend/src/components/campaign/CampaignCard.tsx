import { Link } from 'react-router-dom'
import { StatusBadge } from './StatusBadge'
import type { CampaignSummary } from '../../types/campaign'

interface CampaignCardProps {
	campaign: CampaignSummary
}

function formatCurrency(value: number): string {
	return new Intl.NumberFormat('en-US', {
		style: 'currency',
		currency: 'USD',
		maximumFractionDigits: 0,
	}).format(value)
}

function formatDate(iso: string): string {
	if (!iso) {
		return 'Unknown date'
	}
	const date = new Date(iso)
	return date.toLocaleDateString('en-US', {
		month: 'short',
		day: 'numeric',
		year: 'numeric',
	})
}

export function CampaignCard({ campaign }: CampaignCardProps) {
	return (
		<article className="campaign-card">
			<div className="campaign-card-head">
				<h3>{campaign.businessName}</h3>
				<StatusBadge status={campaign.status} />
			</div>

			<dl className="campaign-card-meta">
				<div>
					<dt>Monthly Budget</dt>
					<dd>{formatCurrency(campaign.monthlyBudget)}</dd>
				</div>
				<div>
					<dt>Total Spend</dt>
					<dd>{formatCurrency(campaign.totalSpend)}</dd>
				</div>
				<div>
					<dt>Created</dt>
					<dd>{formatDate(campaign.createdAt)}</dd>
				</div>
			</dl>

			<Link to={`/campaigns/${campaign.id}`} className="campaign-link">
				View campaign
			</Link>
		</article>
	)
}

