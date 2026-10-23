import { apiBaseUrl, apiTimeoutMs } from './config'

export type ResponseMode = 'llm' | 'fallback' | 'no_match'

export interface BudgetInput {
  tier: 'low' | 'medium' | 'high'
  currency: 'INR'
}

export interface RecommendationRequest {
  location: { city: string; locality: string | null }
  budget: BudgetInput | null
  cuisines: string[]
  minimumRating: number | null
  additionalPreferences: string | null
  resultCount: number
}

export interface InterpretedPreferences {
  city: string
  locality: string | null
  budgetRange: {
    minimumMinor: number
    maximumMinor: number | null
    currency: string
    tier: string | null
  } | null
  cuisines: string[]
  minimumRating: number | null
  softPreferenceProvided: boolean
}

export interface Restaurant {
  id: string
  name: string
  city: string | null
  locality: string | null
  cuisines: string[]
  rating: number | null
  ratingScale: number
  estimatedCostMinor: number | null
  currency: string | null
  sourceUrl: string | null
}

export interface RecommendationItem {
  rank: number
  restaurant: Restaurant
  explanation: string
  caveats: string[]
}

export interface Relaxation {
  constraint: 'locality' | 'budget' | 'rating' | 'cuisine'
  description: string
  candidateCount: number
}

export interface RecommendationResponse {
  requestId: string
  datasetVersion: string
  scoringVersion: string
  mode: ResponseMode
  outcome: 'matches' | 'no_match'
  interpretedPreferences: InterpretedPreferences
  recommendations: RecommendationItem[]
  relaxations: Relaxation[]
  warnings: string[]
}

interface ErrorEnvelope {
  requestId: string
  error: {
    code: string
    message: string
    details: Array<{ field: string | null; reason: string }>
  }
}

interface MetadataResponse {
  requestId: string
  values: string[]
}

export class ApiError extends Error {
  constructor(
    public readonly code: string,
    message: string,
    public readonly requestId: string | null,
    public readonly details: ErrorEnvelope['error']['details'] = [],
  ) {
    super(message)
  }
}

export async function getMetadata(
  kind: 'locations' | 'cuisines',
  query: string,
  signal: AbortSignal,
): Promise<string[]> {
  // The active Bangalore dataset currently contains more than 20 localities and
  // cuisines. Request the API maximum so the form does not silently hide valid
  // filters that happen to sort later in the alphabet.
  const params = new URLSearchParams({ query, limit: '100' })
  const response = await request<MetadataResponse>(
    `/api/v1/metadata/${kind}?${params.toString()}`,
    { signal },
  )
  return response.values
}

export function getRecommendations(
  body: RecommendationRequest,
  signal: AbortSignal,
): Promise<RecommendationResponse> {
  return request('/api/v1/recommendations', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  })
}

async function request<T>(path: string, init: RequestInit): Promise<T> {
  const timeout = new AbortController()
  const timer = window.setTimeout(() => timeout.abort(), apiTimeoutMs)
  const signal = init.signal
    ? AbortSignal.any([init.signal, timeout.signal])
    : timeout.signal

  try {
    const response = await fetch(`${apiBaseUrl}${path}`, { ...init, signal })
    const payload: unknown = await response.json().catch(() => null)
    if (!response.ok) {
      if (isErrorEnvelope(payload)) {
        throw new ApiError(
          payload.error.code,
          payload.error.message,
          payload.requestId,
          payload.error.details,
        )
      }
      throw new ApiError(
        response.status === 429 ? 'RATE_LIMITED' : 'SERVICE_UNAVAILABLE',
        response.status === 429
          ? 'Too many requests. Please wait and try again.'
          : 'The recommendation service is unavailable.',
        response.headers.get('X-Request-ID'),
      )
    }
    return payload as T
  } catch (error: unknown) {
    if (timeout.signal.aborted && !init.signal?.aborted) {
      throw new ApiError(
        'REQUEST_TIMEOUT',
        'The recommendation service took too long to respond.',
        null,
      )
    }
    if (error instanceof TypeError) {
      throw new ApiError(
        'NETWORK_ERROR',
        'Unable to reach the recommendation service.',
        null,
      )
    }
    throw error
  } finally {
    window.clearTimeout(timer)
  }
}

function isErrorEnvelope(value: unknown): value is ErrorEnvelope {
  if (!value || typeof value !== 'object') return false
  const candidate = value as Partial<ErrorEnvelope>
  return Boolean(
    candidate.requestId && candidate.error?.code && candidate.error.message,
  )
}
