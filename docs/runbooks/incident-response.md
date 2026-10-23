# Incident response and rollback

## Availability

1. Correlate the alert window with request IDs, status groups, database saturation, Redis health, and provider errors.
2. If Groq is failing, leave the circuit open and confirm deterministic fallback; do not disable structured filtering.
3. If Redis is failing, confirm miss/fail-open behavior and scale conservatively because provider calls increase.
4. If the database is unavailable or no dataset is active, stop promotion and restore dependency or reactivate a validated prior dataset.

## Application rollback

Roll back to the previously recorded image digest with `kubectl rollout undo deployment/nextleap-api`, verify live/ready probes and a deterministic request, then roll back web independently. Database migrations must be backward-compatible for one release; destructive migrations require expand/migrate/contract across releases.

## Dataset rollback

Within a transaction, lock dataset-version rows, mark the current active version `retired`, mark the selected validated/retired prior version `active`, commit, and verify its row count and `/health/ready`. Immutable version IDs naturally switch cache keys. Never edit restaurant rows in place.

## Backup restoration

Restore only into an isolated database first using `scripts/restore-test.sh`. Validate migrations, active-version uniqueness, counts, checksums, representative searches, and audit access. Production restore requires incident commander and database owner approval. Record start/end time to demonstrate the 60-minute RTO and verify the 15-minute RPO.

## Ownership

The service owner leads incidents; the database owner performs restore/migration actions; the security owner reviews secret or injection events; the product owner approves relevance/dataset rollback. Replace these role names with assigned people before launch.
