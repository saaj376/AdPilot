export type CampaignStatus =
	| 'PENDING'
	| 'RUNNING'
	| 'LAUNCHED'
	| 'PAUSED'
	| 'DONE'
	| 'FAILED'

export interface CampaignContext {
	campaign_id: string
	business_description: string
	monthly_budget: number
	geo_targets: string[]
	created_at: string
	campaign_status: CampaignStatus
	business_profile: Record<string, unknown>
	keyword_strategy: Record<string, unknown>
	ad_creatives: Record<string, unknown>
	qa_result: Record<string, unknown>
	campaign_ids: Record<string, unknown>
	performance_data: Record<string, unknown>
	optimizations: Record<string, unknown>
	weekly_report: string
	agent_states: Record<string, import('./agent').AgentRunState>
	campaign?: Record<string, unknown> | null
}

export interface CampaignSummary {
	id: string
	businessName: string
	status: CampaignStatus
	monthlyBudget: number
	createdAt: string
	totalSpend: number
}

