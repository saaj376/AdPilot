import { useEffect, useState } from 'react'
import type { AgentRunState } from '../../types/agent'

interface AgentPipelineProps {
	orderedAgentNames: string[]
	agentStates: Record<string, AgentRunState>
	selectedAgentName?: string
	onSelectAgent?: (agentName: string) => void
}

function statusDotClass(status: AgentRunState['status']): string {
	switch (status) {
		case 'RUNNING':
			return 'dot dot-running'
		case 'DONE':
			return 'dot dot-done'
		case 'FAILED':
			return 'dot dot-failed'
		case 'IDLE':
		default:
			return 'dot dot-idle'
	}
}

function formatDuration(state?: AgentRunState, nowOverride?: number): string {
	if (!state?.started_at) {
		return '--'
	}
	const start = new Date(state.started_at).getTime()
	const end = state.finished_at ? new Date(state.finished_at).getTime() : (nowOverride ?? Date.now())
	const deltaSeconds = Math.max(0, Math.round((end - start) / 1000))
	return `${deltaSeconds}s`
}

export function AgentPipeline({
	orderedAgentNames,
	agentStates,
	selectedAgentName,
	onSelectAgent,
}: AgentPipelineProps) {
	// Re-render every second to update live timers for 'RUNNING' agents
	const [now, setNow] = useState(() => Date.now())

	useEffect(() => {
		const hasRunning = Object.values(agentStates).some((s) => s.status === 'RUNNING')
		if (!hasRunning) return

		const timer = setInterval(() => setNow(Date.now()), 1000)
		return () => clearInterval(timer)
	}, [agentStates])

	return (
		<section className="pipeline-shell">
			<h3>Agent Pipeline Progress</h3>
			<ul className="pipeline-list">
				{orderedAgentNames.map((agentName) => {
					const state = agentStates[agentName]
					const status = state?.status ?? 'IDLE'
					const isSelected = selectedAgentName === agentName
					return (
						<li
							key={agentName}
							className={isSelected ? 'pipeline-item pipeline-item-selected' : 'pipeline-item'}
							onClick={() => onSelectAgent?.(agentName)}
						>
							<span className={statusDotClass(status)} aria-hidden="true" />
							<span className="pipeline-name">{agentName.replace('Agent', '')}</span>
							<span className={`pipeline-status pipeline-${status.toLowerCase()}`}>{status}</span>
							<span className="pipeline-duration">
								{status === 'RUNNING' ? formatDuration(state, now) : formatDuration(state)}
							</span>
						</li>
					)
				})}
			</ul>
		</section>
	)
}


