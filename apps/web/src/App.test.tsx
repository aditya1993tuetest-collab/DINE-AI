import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { App } from './App'
import type { RecommendationResponse } from './api/client'

const matchResponse: RecommendationResponse = {
  requestId: 'req-123',
  datasetVersion: 'dataset-2026',
  scoringVersion: 'score-v1',
  mode: 'llm',
  outcome: 'matches',
  interpretedPreferences: {
    city: 'Bangalore',
    locality: 'Indiranagar',
    budgetRange: null,
    cuisines: ['Italian'],
    minimumRating: 4,
    softPreferenceProvided: true,
  },
  recommendations: [
    {
      rank: 1,
      restaurant: {
        id: 'restaurant-1',
        name: 'Olive & Thyme',
        city: 'Bangalore',
        locality: 'Indiranagar',
        cuisines: ['Italian'],
        rating: 4.4,
        ratingScale: 5,
        estimatedCostMinor: 120000,
        currency: 'INR',
        sourceUrl: null,
      },
      explanation: 'A strong verified match for your selected filters.',
      caveats: [],
    },
  ],
  relaxations: [],
  warnings: [],
}

function json(body: unknown, status = 200) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    }),
  )
}

function mockApi(response: RecommendationResponse = matchResponse) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
    const url = String(input)
    if (url.includes('/metadata/locations'))
      return json({
        requestId: 'meta-1',
        values: ['Indiranagar', 'Koramangala'],
      })
    if (url.includes('/metadata/cuisines'))
      return json({ requestId: 'meta-2', values: ['Italian', 'Indian'] })
    if (url.endsWith('/recommendations')) return json(response)
    return json({}, 404)
  })
}

function recommendationBody() {
  const call = vi
    .mocked(fetch)
    .mock.calls.find(([input]) => String(input).endsWith('/recommendations'))
  return JSON.parse(String(call?.[1]?.body)) as Record<string, unknown>
}

describe('DineAI search', () => {
  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
  })

  it('starts with the approved form and no simulated recommendations', async () => {
    mockApi()
    render(<App />)

    expect(
      screen.getByRole('heading', { name: /Good food/ }),
    ).toBeInTheDocument()
    expect(screen.queryByText('Olive & Thyme')).not.toBeInTheDocument()
    expect(screen.queryByText(/Simulate View State/i)).not.toBeInTheDocument()
    expect(
      await screen.findByRole('option', { name: 'Indiranagar, Bengaluru' }),
    ).toBeInTheDocument()
  })

  it('submits all five fields to the real API contract and renders results', async () => {
    mockApi()
    render(<App />)

    await screen.findByRole('option', { name: 'Indiranagar, Bengaluru' })
    fireEvent.change(screen.getByLabelText(/Select location/), {
      target: { value: 'Indiranagar' },
    })
    fireEvent.change(screen.getByLabelText('Budget'), {
      target: { value: 'high' },
    })
    fireEvent.change(screen.getByLabelText('Cuisine'), {
      target: { value: 'Italian' },
    })
    fireEvent.change(screen.getByLabelText('Minimum rating'), {
      target: { value: '4' },
    })
    fireEvent.change(screen.getByLabelText('Additional preferences'), {
      target: { value: 'A quiet family dinner' },
    })
    fireEvent.click(
      screen.getByRole('button', { name: 'Find My Restaurants ✨' }),
    )

    expect(
      await screen.findByRole('heading', { name: /Olive & Thyme/ }),
    ).toBeInTheDocument()
    expect(screen.getByText('Indiranagar, Bangalore')).toBeInTheDocument()
    expect(
      screen.getByLabelText('Restaurant rating and cost'),
    ).toHaveTextContent('₹1,200 for two')
    expect(screen.getByText(/strong verified match/i)).toBeInTheDocument()
    expect(recommendationBody()).toEqual({
      location: { city: 'Bangalore', locality: 'Indiranagar' },
      budget: { tier: 'high', currency: 'INR' },
      cuisines: ['Italian'],
      minimumRating: 4,
      additionalPreferences: 'A quiet family dinner',
      resultCount: 5,
    })
  })

  it('validates location before sending a recommendation request', async () => {
    const fetchMock = mockApi()
    render(<App />)
    await screen.findByRole('option', { name: 'Indiranagar, Bengaluru' })

    fireEvent.click(
      screen.getByRole('button', { name: 'Find My Restaurants ✨' }),
    )

    expect(screen.getByText('Please select a location.')).toBeInTheDocument()
    expect(
      fetchMock.mock.calls.filter(([input]) =>
        String(input).endsWith('/recommendations'),
      ),
    ).toHaveLength(0)
  })

  it('shows empty results and a retryable API error', async () => {
    const fetchMock = mockApi({
      ...matchResponse,
      outcome: 'no_match',
      recommendations: [],
    })
    render(<App />)
    await screen.findByRole('option', { name: 'Indiranagar, Bengaluru' })
    fireEvent.change(screen.getByLabelText(/Select location/), {
      target: { value: 'Indiranagar' },
    })
    fireEvent.click(
      screen.getByRole('button', { name: 'Find My Restaurants ✨' }),
    )
    expect(
      await screen.findByText('No spots found this time.'),
    ).toBeInTheDocument()

    fetchMock.mockImplementation(async (input) => {
      if (!String(input).endsWith('/recommendations'))
        return json({ requestId: 'meta', values: [] })
      return json({ requestId: 'error' }, 503)
    })
    fireEvent.click(
      screen.getByRole('button', { name: 'Find My Restaurants ✨' }),
    )
    expect(
      await screen.findByText('Oops, something went wrong.'),
    ).toBeInTheDocument()

    const callsBeforeRetry = fetchMock.mock.calls.length
    fireEvent.click(screen.getByRole('button', { name: 'Try Again' }))
    await waitFor(() =>
      expect(fetchMock.mock.calls.length).toBe(callsBeforeRetry + 1),
    )
  })
})
