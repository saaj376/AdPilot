import type { FormEvent } from 'react'

export interface CampaignFormValues {
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
						placeholder="United States, United Kingdom, Canada"
					/>
					<p className="field-hint">Comma-separated regions or countries.</p>
				</div>
			</div>

			{error ? <p className="form-error">{error}</p> : null}

			<button type="submit" className="primary-btn" disabled={submitting}>
				{submitting ? 'Launching...' : 'Launch Campaign'}
			</button>
		</form>
	)
}

