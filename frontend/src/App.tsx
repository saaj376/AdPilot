import { Navigate, Route, Routes } from 'react-router-dom'
import { Sidebar } from './components/layout/Sidebar'
import { HomePage } from './pages/Home'
import { NewCampaignPage } from './pages/NewCampaign'
import { CampaignDetailPage } from './pages/CampaignDetail'
import { ReportsPage } from './pages/Reports'

function App() {
	return (
		<div className="app-shell">
			<Sidebar />
			<main className="app-main">
				<Routes>
					<Route path="/" element={<HomePage />} />
					<Route path="/campaigns/new" element={<NewCampaignPage />} />
					<Route path="/campaigns/:campaignId" element={<CampaignDetailPage />} />
					<Route path="/reports" element={<ReportsPage />} />
					<Route path="*" element={<Navigate to="/" replace />} />
				</Routes>
			</main>
		</div>
	)
}

export default App

