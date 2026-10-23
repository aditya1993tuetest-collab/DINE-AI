const configuredBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? '').trim()

// Same-origin is the safest production default. Local Vite development proxies
// these paths to the API, while split hosting sets VITE_API_BASE_URL at build time.
export const apiBaseUrl = configuredBaseUrl.replace(/\/+$/, '')

const configuredTimeout = Number(import.meta.env.VITE_API_TIMEOUT_MS ?? 20_000)
export const apiTimeoutMs =
  Number.isFinite(configuredTimeout) && configuredTimeout >= 1_000
    ? configuredTimeout
    : 20_000
