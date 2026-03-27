import type { ReactNode } from 'react'

interface TopNavProps {
	title: string
	subtitle?: string
	actions?: ReactNode
}

export function TopNav({ title, subtitle, actions }: TopNavProps) {
	return (
		<header className="top-nav">
			<div>
				<h2>{title}</h2>
				{subtitle ? <p>{subtitle}</p> : null}
			</div>
			{actions ? <div className="top-nav-actions">{actions}</div> : null}
		</header>
	)
}

