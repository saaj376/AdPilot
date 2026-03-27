import type { CampaignStatus } from '../../types/campaign'

interface StatusBadgeProps {
	status: CampaignStatus
}

const labelMap: Record<CampaignStatus, string> = {
	PENDING: 'Pending',
	RUNNING: 'Running',
	LAUNCHED: 'Launched',
	PAUSED: 'Paused',
	DONE: 'Done',
	FAILED: 'Failed',
}

export function StatusBadge({ status }: StatusBadgeProps) {
	return <span className={`status-badge status-${status.toLowerCase()}`}>{labelMap[status]}</span>
}

