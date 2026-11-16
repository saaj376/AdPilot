import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { CampaignForm, type CampaignFormValues } from '../components/campaign/CampaignForm'
import { TopNav } from '../components/layout/TopNav'
import { createCampaign } from '../services/api'

function parseBudget(input: string): number {
	const cleaned = input.replace(/[$,\s]/g, '')
	return Number(cleaned)
}

function parseGeoTargets(input: string): string[] {
	const targets = input
		.split(/[;\n]/)
		.map((item) => item.trim())
		.filter(Boolean)

	return targets.length > 0 ? targets : ['United States']
}

export function NewCampaignPage() {
	const navigate = useNavigate()
	const location = useLocation()
	const source = location.state as { businessDescription?: string; researchBriefId?: string } | null
	const [values, setValues] = useState<CampaignFormValues>({
		businessDescription: source?.businessDescription ?? '',
		landingPageUrl: '',
		monthlyBudgetText: '$500',
		geoTargetsText: 'United States',
	})
	const [submitting, setSubmitting] = useState(false)
	const [error, setError] = useState<string | null>(null)

	const launchCampaign = async (): Promise<void> => {
		setError(null)
		const description = values.businessDescription.trim()
		const budget = parseBudget(values.monthlyBudgetText)

		if (description.length < 20) {
			setError('Business description must be at least 20 characters.')
			return
		}

		if (!Number.isFinite(budget) || budget <= 0) {
			setError('Monthly budget must be greater than 0.')
			return
		}

		try {
			setSubmitting(true)
			const response = await createCampaign({
				research_brief_id: source?.researchBriefId,
				landing_page_url: values.landingPageUrl.trim(),
				business_description: description,
				monthly_budget: budget,
				geo_targets: parseGeoTargets(values.geoTargetsText),
			})
			navigate(`/campaigns/${response.campaign_id}`)
		} catch {
			setError('Failed to launch campaign. Please confirm backend is reachable.')
		} finally {
			setSubmitting(false)
		}
	}

	return (
		<div className="page-shell">
			<TopNav
				title="Create New Campaign"
				subtitle="Fill in business details and launch the full multi-agent pipeline"
			/>

			{source?.researchBriefId && <p className="research-intro">Your research brief is attached. Its findings will guide keyword and ad themes. Confirm your product facts and add your business website before continuing.</p>}
			<CampaignForm
				values={values}
				submitting={submitting}
				error={error}
				onChange={setValues}
				onSubmit={launchCampaign}
			/>
		</div>
	)
}

