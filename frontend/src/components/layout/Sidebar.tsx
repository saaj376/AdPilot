import { NavLink } from 'react-router-dom'

const navItems = [
	{ to: '/', label: 'Video Research' },
	{ to: '/campaigns', label: 'Campaigns' },
	{ to: '/campaigns/new', label: 'New Campaign' },
	{ to: '/reports', label: 'Reports' },
]

export function Sidebar() {
	return (
		<aside className="sidebar-shell">
			<div className="brand-box">
				<span className="brand-mark">AD</span>
				<div>
					<h1>AdPilot AI</h1>
					<p>Evidence to Experiments</p>
				</div>
			</div>

			<nav className="sidebar-nav">
				{navItems.map((item) => (
					<NavLink
						key={item.to}
						to={item.to}
						end={item.to === '/'}
						className={({ isActive }) =>
							isActive ? 'sidebar-link sidebar-link-active' : 'sidebar-link'
						}
					>
						{item.label}
					</NavLink>
				))}
			</nav>

			<footer className="sidebar-footer">
				<strong>AdPilot Core</strong>
				<span>Command Center</span>
			</footer>
		</aside>
	)
}

