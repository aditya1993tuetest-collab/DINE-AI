import {
  type FormEvent,
  type ReactNode,
  useEffect,
  useRef,
  useState,
} from 'react'

import {
  ApiError,
  getMetadata,
  getRecommendations,
  type RecommendationItem,
  type RecommendationRequest,
  type RecommendationResponse,
} from './api/client'
import './styles.css'

type Budget = '' | 'low' | 'medium' | 'high'
type MetadataState = 'loading' | 'ready' | 'error'
type SearchState =
  | { kind: 'idle' }
  | { kind: 'loading' }
  | { kind: 'success'; response: RecommendationResponse }
  | { kind: 'error'; message: string; requestId: string | null }

interface FormValues {
  location: string
  budget: Budget
  cuisine: string
  minimumRating: string
  additionalPreferences: string
}

const initialValues: FormValues = {
  location: '',
  budget: 'medium',
  cuisine: '',
  minimumRating: '',
  additionalPreferences: '',
}

export function App() {
  const [values, setValues] = useState(initialValues)
  const [locations, setLocations] = useState<string[]>([])
  const [cuisines, setCuisines] = useState<string[]>([])
  const [metadataState, setMetadataState] = useState<MetadataState>('loading')
  const [metadataAttempt, setMetadataAttempt] = useState(0)
  const [locationError, setLocationError] = useState('')
  const [state, setState] = useState<SearchState>({ kind: 'idle' })
  const requestRef = useRef<AbortController | null>(null)
  const lastRequestRef = useRef<RecommendationRequest | null>(null)
  const outputRef = useRef<HTMLElement>(null)

  useEffect(() => {
    const controller = new AbortController()
    setMetadataState('loading')
    void Promise.all([
      getMetadata('locations', '', controller.signal),
      getMetadata('cuisines', '', controller.signal),
    ])
      .then(([locationValues, cuisineValues]) => {
        setLocations(locationValues)
        setCuisines(cuisineValues)
        setMetadataState('ready')
      })
      .catch((error: unknown) => {
        if (!isAbort(error)) setMetadataState('error')
      })
    return () => controller.abort()
  }, [metadataAttempt])

  useEffect(() => () => requestRef.current?.abort(), [])

  useEffect(() => {
    if (state.kind !== 'idle') outputRef.current?.focus()
  }, [state])

  function update<K extends keyof FormValues>(key: K, value: FormValues[K]) {
    setValues((current) => ({ ...current, [key]: value }))
    if (key === 'location') setLocationError('')
  }

  async function runSearch(request: RecommendationRequest) {
    if (requestRef.current) return
    const controller = new AbortController()
    requestRef.current = controller
    lastRequestRef.current = request
    setState({ kind: 'loading' })

    let timedOut = false
    const timeout = window.setTimeout(() => {
      timedOut = true
      controller.abort()
    }, 20_000)

    try {
      const response = await getRecommendations(request, controller.signal)
      setState({ kind: 'success', response })
    } catch (error: unknown) {
      if (!isAbort(error) || timedOut) {
        const message = timedOut
          ? 'The search took too long. Please try again.'
          : error instanceof ApiError
            ? error.message
            : 'Please check your connection and try again.'
        setState({
          kind: 'error',
          message,
          requestId: error instanceof ApiError ? error.requestId : null,
        })
      }
    } finally {
      window.clearTimeout(timeout)
      if (requestRef.current === controller) requestRef.current = null
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!values.location) {
      setLocationError('Please select a location.')
      document.querySelector<HTMLSelectElement>('#location')?.focus()
      return
    }
    await runSearch(toRequest(values))
  }

  const recommendations =
    state.kind === 'success' ? state.response.recommendations.slice(0, 5) : []
  const isEmpty =
    state.kind === 'success' &&
    (state.response.outcome === 'no_match' || recommendations.length === 0)

  return (
    <div className="app-shell">
      <Header />
      <main className="page-content">
        <Hero />
        <SearchForm
          values={values}
          locations={locations}
          cuisines={cuisines}
          metadataState={metadataState}
          locationError={locationError}
          isLoading={state.kind === 'loading'}
          onUpdate={update}
          onSubmit={submit}
          onRetryMetadata={() => setMetadataAttempt((value) => value + 1)}
        />
        <section
          className="search-output"
          ref={outputRef}
          tabIndex={state.kind === 'idle' ? undefined : -1}
          aria-live="polite"
          aria-busy={state.kind === 'loading'}
        >
          {state.kind === 'loading' && <LoadingState />}
          {state.kind === 'error' && (
            <ErrorState
              message={state.message}
              requestId={state.requestId}
              onRetry={() => {
                if (lastRequestRef.current)
                  void runSearch(lastRequestRef.current)
              }}
            />
          )}
          {isEmpty && <EmptyState />}
          {state.kind === 'success' && !isEmpty && (
            <Results recommendations={recommendations} />
          )}
        </section>
      </main>
      <Footer />
    </div>
  )
}

function Header() {
  return (
    <header className="site-header">
      <div className="header-inner">
        <a className="brand" href="#top" aria-label="DineAI home">
          Dine<b>AI</b>
        </a>
        <p>Good food. Good mood.</p>
      </div>
    </header>
  )
}

function Hero() {
  return (
    <section className="hero" id="top" aria-labelledby="page-title">
      <span className="kicker">Your food. Your vibe.</span>
      <h1 id="page-title">
        Good food. <em>Zero guesswork.</em>
      </h1>
      <p>
        Tell us what you&apos;re craving, and let AI find your next favorite
        food spot.
      </p>
    </section>
  )
}

interface SearchFormProps {
  values: FormValues
  locations: string[]
  cuisines: string[]
  metadataState: MetadataState
  locationError: string
  isLoading: boolean
  onUpdate: <K extends keyof FormValues>(key: K, value: FormValues[K]) => void
  onSubmit: (event: FormEvent<HTMLFormElement>) => Promise<void>
  onRetryMetadata: () => void
}

function SearchForm(props: SearchFormProps) {
  const {
    values,
    locations,
    cuisines,
    metadataState,
    locationError,
    isLoading,
    onUpdate,
    onSubmit,
    onRetryMetadata,
  } = props
  return (
    <section className="search-card" aria-labelledby="form-title">
      <div className="card-heading">
        <div>
          <h2 id="form-title">Let&apos;s find your food spot. ✨</h2>
          <p>A few quick preferences, and we&apos;ll handle the rest.</p>
        </div>
        <TuneIcon />
      </div>
      {metadataState === 'error' && (
        <div className="metadata-alert" role="alert">
          <span>We couldn&apos;t load the available filters.</span>
          <button type="button" onClick={onRetryMetadata}>
            Try again
          </button>
        </div>
      )}
      <form onSubmit={(event) => void onSubmit(event)} noValidate>
        <div className="form-grid">
          <label className="field" htmlFor="location">
            <span>
              Select location <b aria-hidden="true">*</b>
            </span>
            <SelectShell>
              <select
                id="location"
                value={values.location}
                onChange={(event) => onUpdate('location', event.target.value)}
                disabled={metadataState !== 'ready' || isLoading}
                aria-invalid={Boolean(locationError)}
                aria-describedby={locationError ? 'location-error' : undefined}
                required
              >
                <option value="">
                  {metadataState === 'loading'
                    ? 'Loading locations…'
                    : 'Where are we eating?'}
                </option>
                {locations.map((location) => (
                  <option key={location} value={location}>
                    {location}, Bengaluru
                  </option>
                ))}
              </select>
            </SelectShell>
            {locationError && (
              <small className="field-error" id="location-error">
                {locationError}
              </small>
            )}
          </label>

          <label className="field" htmlFor="budget">
            <span>Budget</span>
            <SelectShell>
              <select
                id="budget"
                value={values.budget}
                onChange={(event) =>
                  onUpdate('budget', event.target.value as Budget)
                }
                disabled={isLoading}
              >
                <option value="">Any Budget</option>
                <option value="low">Low (under ₹600 for two)</option>
                <option value="medium">Medium (₹600–₹1,500 for two)</option>
                <option value="high">High (₹1,500+ for two)</option>
              </select>
            </SelectShell>
          </label>

          <label className="field" htmlFor="cuisine">
            <span>Cuisine</span>
            <SelectShell>
              <select
                id="cuisine"
                value={values.cuisine}
                onChange={(event) => onUpdate('cuisine', event.target.value)}
                disabled={metadataState !== 'ready' || isLoading}
              >
                <option value="">
                  {metadataState === 'loading'
                    ? 'Loading cuisines…'
                    : 'What are you craving? (Any Cuisine)'}
                </option>
                {cuisines.map((cuisine) => (
                  <option key={cuisine} value={cuisine}>
                    {cuisine}
                  </option>
                ))}
              </select>
            </SelectShell>
          </label>

          <label className="field" htmlFor="minimum-rating">
            <span>Minimum rating</span>
            <SelectShell>
              <select
                id="minimum-rating"
                value={values.minimumRating}
                onChange={(event) =>
                  onUpdate('minimumRating', event.target.value)
                }
                disabled={isLoading}
              >
                <option value="">Any Rating</option>
                <option value="3">3.0+</option>
                <option value="3.5">3.5+</option>
                <option value="4">4.0+</option>
                <option value="4.5">4.5+</option>
              </select>
            </SelectShell>
          </label>

          <label className="field preferences-field" htmlFor="preferences">
            <span>Additional preferences</span>
            <textarea
              id="preferences"
              value={values.additionalPreferences}
              onChange={(event) =>
                onUpdate('additionalPreferences', event.target.value)
              }
              disabled={isLoading}
              maxLength={500}
              rows={2}
              placeholder="Something cozy? A family dinner? Tell us your vibe…"
            />
          </label>
        </div>
        <button
          className="submit-button"
          type="submit"
          disabled={isLoading || metadataState !== 'ready'}
        >
          {isLoading
            ? 'Finding your next favorite spot... ✨'
            : 'Find My Restaurants ✨'}
        </button>
      </form>
    </section>
  )
}

function SelectShell({ children }: { children: ReactNode }) {
  return (
    <div className="select-wrap">
      {children}
      <ChevronIcon />
    </div>
  )
}

function LoadingState() {
  return (
    <div className="status-state">
      <span className="spinner" aria-hidden="true" />
      <h2>Finding your next favorite spot... ✨</h2>
      <p>Matching your preferences with verified restaurant data.</p>
    </div>
  )
}

function EmptyState() {
  return (
    <div className="status-state">
      <span className="status-icon" aria-hidden="true">
        ⌕
      </span>
      <h2>No spots found this time.</h2>
      <p>Try adjusting your preferences and search again.</p>
    </div>
  )
}

function ErrorState({
  message,
  requestId,
  onRetry,
}: {
  message: string
  requestId: string | null
  onRetry: () => void
}) {
  return (
    <div className="status-state error-state" role="alert">
      <span className="status-icon" aria-hidden="true">
        !
      </span>
      <h2>Oops, something went wrong.</h2>
      <p>{message}</p>
      {requestId && <small>Support reference: {requestId}</small>}
      <button type="button" onClick={onRetry}>
        Try Again
      </button>
    </div>
  )
}

function Results({
  recommendations,
}: {
  recommendations: RecommendationItem[]
}) {
  return (
    <div className="results-view">
      <div className="results-heading">
        <span>Made for your taste</span>
        <h2>Your next favorite spots.</h2>
        <p>Handpicked by AI, based on what you love.</p>
      </div>
      <div className="result-list">
        {recommendations.map((item, index) => (
          <RestaurantCard key={item.restaurant.id} item={item} index={index} />
        ))}
      </div>
    </div>
  )
}

function RestaurantCard({
  item,
  index,
}: {
  item: RecommendationItem
  index: number
}) {
  const { restaurant } = item
  const location = [restaurant.locality, restaurant.city]
    .filter(Boolean)
    .join(', ')
  return (
    <article className="result-card">
      <div className="restaurant-topline">
        <div>
          <h3>
            {String(index + 1).padStart(2, '0')} — {restaurant.name}
          </h3>
          <div className="restaurant-meta">
            {restaurant.cuisines.length > 0 && (
              <span className="cuisine-pill">
                {restaurant.cuisines.join(' • ')}
              </span>
            )}
            {location && (
              <span className="location-text">
                <PinIcon /> {location}
              </span>
            )}
          </div>
        </div>
        <div
          className="restaurant-facts"
          aria-label="Restaurant rating and cost"
        >
          {restaurant.rating !== null && (
            <span className="rating-pill">
              <b aria-hidden="true">★</b> {formatRating(restaurant.rating)}
            </span>
          )}
          {restaurant.estimatedCostMinor !== null && restaurant.currency && (
            <span>
              {formatCost(restaurant.estimatedCostMinor, restaurant.currency)}{' '}
              for two
            </span>
          )}
        </div>
      </div>
      {item.explanation && (
        <div className="explanation">
          <span>Why it&apos;s your vibe ✨</span>
          <p>{item.explanation}</p>
        </div>
      )}
      {item.caveats.length > 0 && (
        <p className="caveat">Note: {item.caveats.join(' ')}</p>
      )}
    </article>
  )
}

function Footer() {
  return (
    <footer>
      <div>
        <a className="brand brand-small" href="#top">
          Dine<b>AI</b>
        </a>
        <p>Made for food lovers. ✨</p>
      </div>
    </footer>
  )
}

function TuneIcon() {
  return (
    <svg className="tune-icon" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 7h10M18 7h2M4 17h2M10 17h10M8 14v6M16 4v6" />
    </svg>
  )
}

function ChevronIcon() {
  return (
    <svg className="chevron-icon" viewBox="0 0 20 20" aria-hidden="true">
      <path d="m6.5 8 3.5 3.5L13.5 8" />
    </svg>
  )
}

function PinIcon() {
  return (
    <svg className="pin-icon" viewBox="0 0 20 20" aria-hidden="true">
      <path d="M10 17s5-4.45 5-9a5 5 0 1 0-10 0c0 4.55 5 9 5 9Z" />
      <circle cx="10" cy="8" r="1.7" />
    </svg>
  )
}

function toRequest(values: FormValues): RecommendationRequest {
  return {
    location: { city: 'Bangalore', locality: values.location },
    budget: values.budget ? { tier: values.budget, currency: 'INR' } : null,
    cuisines: values.cuisine ? [values.cuisine] : [],
    minimumRating: values.minimumRating ? Number(values.minimumRating) : null,
    additionalPreferences: values.additionalPreferences.trim() || null,
    resultCount: 5,
  }
}

function formatRating(value: number): string {
  return Number.isInteger(value) ? value.toFixed(1) : String(value)
}

function formatCost(minor: number, currency: string): string {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency,
    maximumFractionDigits: 0,
  }).format(minor / 100)
}

function isAbort(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'AbortError'
}
