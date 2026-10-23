# Phase 4 web experience

The React application provides the complete recommendation workflow described in Phase 4 of the implementation plan. It uses metadata-assisted location and cuisine inputs, client validation, cancellable API requests, ranked results, explicit fallback and no-match states, stable error messages, and request IDs for support.

## Local configuration

Create an untracked `.env` in the repository root from `.env.example`. For Groq, set `LLM_PROVIDER=groq`, `LLM_MODEL=openai/gpt-oss-120b`, and `LLM_API_KEY` to a current secret. Never place the key in `.env.example` or commit it. `compose.yaml` forwards those root variables to the API container.

Run the application with `docker compose up --build`, or run the API and web packages separately. The browser defaults to same-origin API paths. Vite proxies them to `http://127.0.0.1:8000` in local development and Nginx proxies them to the API container. Set `VITE_API_BASE_URL` at web build time only for split-origin hosting.

## Verification

From `apps/web`, run:

```text
npm run format:check
npm run lint
npm run typecheck
npm test
npm run build
npx playwright install chromium
npm run test:e2e
```

The Playwright suite covers normal results, no-match relaxation guidance, deterministic fallback, client validation, server errors, mobile rendering, and automated serious/critical accessibility checks. A release still requires a manual keyboard and screen-reader smoke test because automated checks cannot prove complete accessibility.

## Manual accessibility smoke test

Before release, test at 200% browser zoom and at a 320 CSS-pixel viewport. Complete a search using only Tab, Shift+Tab, Space, Enter, and arrow keys; confirm visible focus, logical focus order, validation focus, loading announcements, result focus, and the edit-preferences return path. With NVDA or VoiceOver, confirm form labels, optional/required meaning, result rank, rating scale, estimated cost, caveats, fallback notices, and errors with support references are announced clearly.
