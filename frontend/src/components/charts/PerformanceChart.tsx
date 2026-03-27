import {
	CartesianGrid,
	Line,
	LineChart,
	ResponsiveContainer,
	Tooltip,
	XAxis,
	YAxis,
} from 'recharts'

export interface PerformancePoint {
	label: string
	ctr: number
	cpc: number
}

interface PerformanceChartProps {
	data: PerformancePoint[]
}

export function PerformanceChart({ data }: PerformanceChartProps) {
	return (
		<div className="chart-shell">
			<h4>CTR and CPC Trend</h4>
			<ResponsiveContainer width="100%" height={230}>
				<LineChart data={data}>
					<CartesianGrid strokeDasharray="3 3" stroke="rgba(91,114,142,0.35)" />
					<XAxis dataKey="label" stroke="#6f8099" />
					<YAxis yAxisId="left" stroke="#6f8099" />
					<YAxis yAxisId="right" orientation="right" stroke="#6f8099" />
					<Tooltip />
					<Line yAxisId="left" type="monotone" dataKey="ctr" stroke="#30c48d" strokeWidth={3} dot={false} />
					<Line yAxisId="right" type="monotone" dataKey="cpc" stroke="#3f78ff" strokeWidth={3} dot={false} />
				</LineChart>
			</ResponsiveContainer>
		</div>
	)
}

