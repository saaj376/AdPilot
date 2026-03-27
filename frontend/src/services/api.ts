import type {
	CampaignContext,
	CampaignIdsResponse,
	CampaignStatusResponse,
	CreateCampaignRequest,
	CreateCampaignResponse,
	ReportResponse,
} from '../types/api'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:8000'

class ApiError extends Error {
	status: number
	body: unknown

	constructor(message: string, status: number, body: unknown) {
		super(message)
		this.name = 'ApiError'
		this.status = status
		this.body = body
	}
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
	const response = await fetch(`${API_BASE_URL}${path}`, {
		headers: {
			'Content-Type': 'application/json',
			...(init?.headers ?? {}),
		},
		...init,
	})

	if (!response.ok) {
		let body: unknown = null
		try {
			body = await response.json()
		} catch {
			body = await response.text()
		}
		throw new ApiError(`Request failed for ${path}`, response.status, body)
	}

	return (await response.json()) as T
}

export async function getCampaignIds(): Promise<CampaignIdsResponse> {
	return request<CampaignIdsResponse>('/campaigns')
}

export async function getCampaignStatus(campaignId: string): Promise<CampaignStatusResponse> {
	return request<CampaignStatusResponse>(`/campaigns/${campaignId}/status`)
}

export async function getCampaign(campaignId: string): Promise<CampaignContext> {
	return request<CampaignContext>(`/campaigns/${campaignId}`)
}

export async function createCampaign(payload: CreateCampaignRequest): Promise<CreateCampaignResponse> {
	return request<CreateCampaignResponse>('/campaigns', {
		method: 'POST',
		body: JSON.stringify(payload),
	})
}

export async function getReport(campaignId: string): Promise<ReportResponse> {
	return request<ReportResponse>(`/reports/${campaignId}`)
}

export function isApiError(error: unknown): error is ApiError {
	return error instanceof ApiError
}

export function getApiBaseUrl(): string {
	return API_BASE_URL
}

