import { afterEach, describe, expect, it, vi } from 'vitest'

import { ApiError, getMetadata, getRecommendations } from './client'

describe('API client', () => {
  afterEach(() => vi.restoreAllMocks())

  it('uses the versioned endpoint and serializes the typed request', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ outcome: 'no_match' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    const controller = new AbortController()
    await getRecommendations(
      {
        location: { city: 'Bangalore', locality: null },
        budget: null,
        cuisines: [],
        minimumRating: null,
        additionalPreferences: null,
        resultCount: 5,
      },
      controller.signal,
    )

    expect(
      String(fetchMock.mock.calls[0][0]).endsWith('/api/v1/recommendations'),
    ).toBe(true)
    expect(fetchMock.mock.calls[0][1]).toMatchObject({
      method: 'POST',
      signal: controller.signal,
    })
  })

  it('maps structured API errors and preserves request IDs', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({
          requestId: 'req-error',
          error: {
            code: 'INVALID_PREFERENCE',
            message: 'Invalid rating',
            details: [],
          },
        }),
        { status: 422, headers: { 'Content-Type': 'application/json' } },
      ),
    )

    await expect(
      getMetadata('cuisines', 'ita', new AbortController().signal),
    ).rejects.toMatchObject({
      code: 'INVALID_PREFERENCE',
      requestId: 'req-error',
    } satisfies Partial<ApiError>)
  })

  it('passes cancellation signals through to fetch', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockRejectedValue(new DOMException('aborted', 'AbortError'))
    const controller = new AbortController()
    controller.abort()
    await expect(
      getMetadata('locations', '', controller.signal),
    ).rejects.toHaveProperty('name', 'AbortError')
    expect(fetchMock.mock.calls[0][1]?.signal).toBeInstanceOf(AbortSignal)
    expect(fetchMock.mock.calls[0][1]?.signal?.aborted).toBe(true)
  })

  it('uses same-origin API paths when no deployment URL is configured', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ requestId: 'meta', values: [] }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    await getMetadata('locations', '', new AbortController().signal)

    expect(String(fetchMock.mock.calls[0][0])).toBe(
      '/api/v1/metadata/locations?query=&limit=100',
    )
  })
})
