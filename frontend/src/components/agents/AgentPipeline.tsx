import type { AgentRunState } from '../../types/agent'

interface AgentPipelineProps {
	orderedAgentNames: string[]
	agentStates: Record<string, AgentRunState>
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

function formatDuration(state?: AgentRunState): string {
	if (!state?.started_at || !state?.finished_at) {
		return '--'
	}
	const start = new Date(state.started_at).getTime()
	const finish = new Date(state.finished_at).getTime()
	const deltaSeconds = Math.max(0, Math.round((finish - start) / 1000))
	return `${deltaSeconds}s`
}

export function AgentPipeline({ orderedAgentNames, agentStates }: AgentPipelineProps) {
	return (
		<section className="pipeline-shell">
			<h3>Agent Pipeline Progress</h3>
			<ul className="pipeline-list">
				{orderedAgentNames.map((agentName) => {
					const state = agentStates[agentName]
					const status = state?.status ?? 'IDLE'
					return (
						<li key={agentName} className="pipeline-item">
							<span className={statusDotClass(status)} aria-hidden="true" />
							<span className="pipeline-name">{agentName.replace('Agent', '')}</span>
							<span className={`pipeline-status pipeline-${status.toLowerCase()}`}>{status}</span>
							<span className="pipeline-duration">{formatDuration(state)}</span>
						</li>
					)
				})}
			</ul>
		</section>
	)
}

