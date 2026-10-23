import { apiBaseUrl } from './config'

export interface LiveHealth {
  status: 'ok'
  service: 'restaurant-recommendation-api'
  version: string
}

export async function getLiveHealth(signal?: AbortSignal): Promise<LiveHealth> {
  const response = await fetch(`${apiBaseUrl}/health/live`, { signal })

  if (!response.ok) {
    throw new Error(`Health request failed with status ${response.status}`)
  }

  return (await response.json()) as LiveHealth
}
