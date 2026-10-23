# Lightweight threat model

| Threat | Control | Verification |
|---|---|---|
| Prompt injection through free text | Structured candidate allowlist, grounded-output guard, bounded text, no tool access | Adversarial API tests and Phase 3 guard tests |
| SQL injection | SQLAlchemy bound expressions; no user-composed SQL | Static review and malicious metadata/request tests |
| Stored/reflected XSS | React text rendering, no raw HTML, CSP | Playwright payload test and CSP scan |
| LLM/data exfiltration | Candidate-only prompt, no credentials, hashed telemetry | Telemetry review and provider adapter tests |
| Cost/denial of service | Shared rate limits, body/schema ceilings, cache, provider timeout/circuit | 429/body-limit and failure-injection tests |
| Secret disclosure | `.env` excluded, deployment secret manager, secret scanning | Gitleaks CI gate |
| Dependency/container compromise | Audit, Trivy, SBOM, non-root/read-only containers | CI release gates |
| Cache poisoning/cross-version stale data | Canonical versioned keys and response revalidation | Cache-key unit tests |
| Spoofed client/request identifiers | Hashed socket IP; constrained request-ID alphabet/length | API tests; proxy headers disabled by default |

Residual risks requiring platform review are ingress TLS/HSTS, cloud IAM/least-privilege role grants, managed Redis authentication, egress enforcement, backup encryption, and third-party provider retention.
