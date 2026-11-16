import type { CampaignContext, CampaignStatus } from './campaign'

export interface CreateCampaignRequest {
	research_brief_id?: string
	landing_page_url?: string
	business_description: string
	monthly_budget: number
	geo_targets: string[]
}

export interface CreateCampaignResponse {
	campaign_id: string
	status: CampaignStatus
	message: string
}

export interface CampaignIdsResponse {
	campaign_ids: string[]
	count: number
}

export interface CampaignStatusResponse {
	campaign_id: string
	campaign_status: CampaignStatus
	agent_states: Record<
		string,
		{
			status: 'IDLE' | 'RUNNING' | 'DONE' | 'FAILED'
			started_at: string | null
			finished_at: string | null
		}
	>
}

export interface ReportResponse {
	campaign_id: string
	campaign_status: CampaignStatus
	weekly_report: string
	performance_data: Record<string, unknown>
	optimizations: Record<string, unknown>
	business_name: string
	created_at: string
}

export type { CampaignContext }

