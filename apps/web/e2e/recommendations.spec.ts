import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Page } from '@playwright/test'

const matchResponse = {
  requestId: 'req-e2e',
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
        id: '1',
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
      explanation: 'A grounded match for the selected preferences.',
      caveats: [],
    },
  ],
  relaxations: [],
  warnings: [],
}

async function mockMetadata(page: Page) {
  await page.route('**/api/v1/metadata/**', (route) =>
    route.fulfill({
      json: {
        requestId: 'meta',
        values: route.request().url().includes('cuisines')
          ? ['Italian', 'Indian']
          : ['Indiranagar', 'Koramangala'],
      },
    }),
  )
}

async function chooseLocation(page: Page) {
  await page.getByLabel(/Select location/).selectOption('Indiranagar')
}

test('search sends all preferences and renders grounded API results', async ({
  page,
}) => {
  let submitted: Record<string, unknown> | undefined
  await mockMetadata(page)
  await page.route('**/api/v1/recommendations', async (route) => {
    submitted = route.request().postDataJSON() as Record<string, unknown>
    await route.fulfill({ json: matchResponse })
  })

  await page.goto('/')
  await chooseLocation(page)
  await page.getByLabel('Budget').selectOption('high')
  await page.getByLabel('Cuisine').selectOption('Italian')
  await page.getByLabel('Minimum rating').selectOption('4')
  await page.getByLabel('Additional preferences').fill('A quiet family dinner')
  await page.getByRole('button', { name: 'Find My Restaurants ✨' }).click()

  await expect(
    page.getByRole('heading', { name: /Olive & Thyme/ }),
  ).toBeVisible()
  await expect(page.getByText('Indiranagar, Bangalore')).toBeVisible()
  await expect(
    page.getByText('A grounded match for the selected preferences.'),
  ).toBeVisible()
  expect(submitted).toEqual({
    location: { city: 'Bangalore', locality: 'Indiranagar' },
    budget: { tier: 'high', currency: 'INR' },
    cuisines: ['Italian'],
    minimumRating: 4,
    additionalPreferences: 'A quiet family dinner',
    resultCount: 5,
  })
})

test('location is required and optional fields may stay empty', async ({
  page,
}) => {
  await mockMetadata(page)
  await page.route('**/api/v1/recommendations', (route) =>
    route.fulfill({ json: matchResponse }),
  )
  await page.goto('/')

  await page.getByRole('button', { name: 'Find My Restaurants ✨' }).click()
  await expect(page.getByText('Please select a location.')).toBeVisible()

  await chooseLocation(page)
  await page.getByLabel('Budget').selectOption('')
  await page.getByRole('button', { name: 'Find My Restaurants ✨' }).click()
  await expect(
    page.getByRole('heading', { name: /Olive & Thyme/ }),
  ).toBeVisible()
})

test('no matches show the approved empty state', async ({ page }) => {
  await mockMetadata(page)
  await page.route('**/api/v1/recommendations', (route) =>
    route.fulfill({
      json: { ...matchResponse, outcome: 'no_match', recommendations: [] },
    }),
  )
  await page.goto('/')
  await chooseLocation(page)
  await page.getByRole('button', { name: 'Find My Restaurants ✨' }).click()

  await expect(page.getByText('No spots found this time.')).toBeVisible()
  await expect(
    page.getByText('Try adjusting your preferences and search again.'),
  ).toBeVisible()
})

test('API failures show an error and retry performs a real request', async ({
  page,
}) => {
  let attempts = 0
  await mockMetadata(page)
  await page.route('**/api/v1/recommendations', async (route) => {
    attempts += 1
    if (attempts === 1) {
      await route.fulfill({ status: 503, json: { requestId: 'failed' } })
      return
    }
    await route.fulfill({ json: matchResponse })
  })
  await page.goto('/')
  await chooseLocation(page)
  await page.getByRole('button', { name: 'Find My Restaurants ✨' }).click()
  await expect(page.getByText('Oops, something went wrong.')).toBeVisible()
  await page.getByRole('button', { name: 'Try Again' }).click()

  await expect(
    page.getByRole('heading', { name: /Olive & Thyme/ }),
  ).toBeVisible()
  expect(attempts).toBe(2)
})

test('the form has no detectable serious accessibility violations', async ({
  page,
}) => {
  await mockMetadata(page)
  await page.route('**/api/v1/recommendations', (route) =>
    route.fulfill({ json: matchResponse }),
  )
  await page.goto('/')
  await expect(page.getByLabel(/Select location/)).toBeEnabled()
  const results = await new AxeBuilder({ page }).analyze()
  expect(
    results.violations.filter((item) =>
      ['serious', 'critical'].includes(item.impact ?? ''),
    ),
  ).toEqual([])
})
