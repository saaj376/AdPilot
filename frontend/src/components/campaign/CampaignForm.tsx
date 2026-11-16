import type { FormEvent } from 'react'

export interface CampaignFormValues {
	landingPageUrl: string
	businessDescription: string
	monthlyBudgetText: string
	geoTargetsText: string
}

interface CampaignFormProps {
	values: CampaignFormValues
	submitting: boolean
	error: string | null
	onChange: (next: CampaignFormValues) => void
	onSubmit: () => Promise<void>
}

export function CampaignForm({
	values,
	submitting,
	error,
	onChange,
	onSubmit,
}: CampaignFormProps) {
	const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
		event.preventDefault()
		await onSubmit()
	}

	const descriptionLength = values.businessDescription.trim().length

	return (
		<form className="campaign-form" onSubmit={handleSubmit}>
			<label htmlFor="description" className="field-label">
				Business Description
			</label>
			<textarea
				id="description"
				className="field-textarea"
				placeholder="Describe your business, services, target customers, and competitive edge..."
				value={values.businessDescription}
				onChange={(event) =>
					onChange({
						...values,
						businessDescription: event.target.value,
					})
				}
				maxLength={1000}
				required
			/>
			<p className="field-hint">Minimum 20 characters. Current: {descriptionLength}</p>

			<label htmlFor="landing-page" className="field-label">Business Website</label>
			<input id="landing-page" className="field-input" type="url" required
				placeholder="https://your-business.com" value={values.landingPageUrl}
				onChange={(event) => onChange({ ...values, landingPageUrl: event.target.value })} />

			<div className="form-grid-two">
				<div>
					<label htmlFor="budget" className="field-label">
						Monthly Budget (USD)
					</label>
					<input
						id="budget"
						className="field-input"
						value={values.monthlyBudgetText}
						onChange={(event) =>
							onChange({
								...values,
								monthlyBudgetText: event.target.value,
							})
						}
						placeholder="$1500"
						required
					/>
				</div>

				<div>
					<label htmlFor="geo" className="field-label">
						Geo Targets
					</label>
					<input
						id="geo"
						className="field-input"
						value={values.geoTargetsText}
						onChange={(event) =>
							onChange({
								...values,
								geoTargetsText: event.target.value,
							})
						}
						placeholder="Austin, TX; Dallas, TX"
					/>
					<p className="field-hint">Separate locations with semicolons, e.g. Austin, TX; Dallas, TX.</p>
				</div>
			</div>

			{error ? <p className="form-error">{error}</p> : null}

			<button type="submit" className="primary-btn" disabled={submitting}>
				{submitting ? 'Launching...' : 'Launch Campaign'}
			</button>
		</form>
	)
}

