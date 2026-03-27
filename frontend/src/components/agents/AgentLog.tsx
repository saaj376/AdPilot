interface AgentLogProps {
	lines: string[]
}

export function AgentLog({ lines }: AgentLogProps) {
	return (
		<section className="log-shell">
			<div className="log-head">
				<span className="log-lamp" />
				<span className="log-lamp amber" />
				<span className="log-lamp green" />
				<strong>Live Agent Log</strong>
			</div>

			<pre className="log-body">
				{lines.length === 0
					? '[waiting] connect to live stream for agent output...'
					: lines.slice(-120).join('\n')}
			</pre>
		</section>
	)
}

