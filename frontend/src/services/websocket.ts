import { getApiBaseUrl } from './api'
import type { CampaignWsMessage } from '../types/agent'

function buildWsUrl(campaignId: string): string {
	const baseUrl = getApiBaseUrl()
	const wsBase = baseUrl.replace(/^http/, 'ws')
	return `${wsBase}/live/${campaignId}`
}

export function connectCampaignWebSocket(
	campaignId: string,
	onMessage: (message: CampaignWsMessage) => void,
	onError?: (event: Event) => void,
): () => void {
	let socket: WebSocket | null = null
	let closedByClient = false
	let attempts = 0
	let completed = false
	let retryTimer: number | undefined

	const connect = () => {
		if (closedByClient) {
			return
		}

		socket = new WebSocket(buildWsUrl(campaignId))

		socket.onopen = () => {
			attempts = 0
		}

		socket.onmessage = (event) => {
			try {
				const payload = JSON.parse(event.data) as CampaignWsMessage
				if (payload.type === 'pipeline_done') completed = true
				onMessage(payload)
			} catch {
				// Ignore malformed payloads and continue streaming future events.
			}
		}

		socket.onerror = (event) => {
			if (onError) {
				onError(event)
			}
		}

		socket.onclose = (event) => {
			if (closedByClient || completed || event.code === 1008) {
				return
			}

			if (onError) {
				onError(event)
			}

			// Retry a few times to recover from transient backend reloads/network hiccups.
			if (attempts < 5) {
				const delayMs = 600 * Math.max(1, attempts + 1)
				attempts += 1
				retryTimer = window.setTimeout(connect, delayMs)
			}
		}
	}

	connect()

	return () => {
		closedByClient = true
		window.clearTimeout(retryTimer)
		if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
			socket.close()
		}
	}
}

