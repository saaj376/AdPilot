interface BudgetGaugeProps {
	spend: number
	monthlyBudget: number
}

function toCurrency(value: number): string {
	return new Intl.NumberFormat('en-US', {
		style: 'currency',
		currency: 'USD',
		maximumFractionDigits: 0,
	}).format(value)
}

export function BudgetGauge({ spend, monthlyBudget }: BudgetGaugeProps) {
	const ratio = monthlyBudget > 0 ? Math.min(1, spend / monthlyBudget) : 0
	const pct = Math.round(ratio * 100)

	return (
		<section className="gauge-shell">
			<h4>Budget Spent</h4>
			<div className="gauge-track" role="img" aria-label={`Budget spent ${pct}%`}>
				<div className="gauge-fill" style={{ width: `${pct}%` }} />
			</div>
			<div className="gauge-meta">
				<strong>{pct}%</strong>
				<span>
					{toCurrency(spend)} of {toCurrency(monthlyBudget)}
				</span>
			</div>
		</section>
	)
}

