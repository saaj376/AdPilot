export type AgentStatus = 'IDLE' | 'RUNNING' | 'DONE' | 'FAILED'

export interface AgentLogItem {
	message: string
	level: 'INFO' | 'WARN' | 'ERROR'
	timestamp: string
}

export interface AgentRunState {
	status: AgentStatus
	started_at: string | null
	finished_at: string | null
	output?: unknown | null
	logs: AgentLogItem[]
}

export interface WebSocketCatchUpMessage {
	type: 'catch_up'
	campaign_id: string
	campaign_status: string
	agent_states: Record<string, AgentRunState>
}

export interface WebSocketAgentUpdateMessage {
	type: 'agent_update'
	campaign_id: string
	agent_name: string
	status: AgentStatus
	output?: unknown | null
	log: AgentLogItem | null
	timestamp: string
}

export interface WebSocketPipelineDoneMessage {
	type: 'pipeline_done'
	campaign_status: import('./campaign').CampaignStatus
	campaign_id: string
}

export type CampaignWsMessage =
	| WebSocketCatchUpMessage
	| WebSocketAgentUpdateMessage
	| WebSocketPipelineDoneMessage

