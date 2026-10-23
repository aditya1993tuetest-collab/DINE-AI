# Phase 1 Data Operations

## Invariants

- Every production ingestion uses an immutable source revision and records its SHA-256.
- Restaurant rows belong to one immutable dataset version.
- Only a validated or retired version may become active.
- Activation and retirement of the previous version occur in one database transaction.
- Versions are retained by default; activation never deletes data.
- Invalid optional rating, cost, or vote fields become unavailable and receive warning codes.
- Missing name, source URL, locality, or cuisine rejects the row.
- Duplicate source URLs retain the first record. A conflicting payload is counted separately.

## Prepare the Database

From `apps/api`, apply the migration:

```powershell
python -m alembic upgrade head
```

Forward recovery is preferred. For a local disposable database, revert with:

```powershell
python -m alembic downgrade base
```

## Profile Without Publishing

From the repository root:

```powershell
nextleap-data ingest --fixture docs/fixtures/restaurants_phase0.csv --dry-run
```

The JSON result contains a generated job ID, duration, coverage, rejection and duplicate counts,
warnings, and gate failures. Dry runs do not write to PostgreSQL.

## Ingest the Pinned Source

Production ingestion is normally run through the manual-only GitHub Actions workflow
`.github/workflows/ingest-zomato.yml`. Configure `RENDER_DATABASE_URL` as an Actions secret, run
`operation: validate`, review the quality and capacity reports, and only then explicitly run
`operation: publish`. Pushes and pull requests cannot start this workflow.

The equivalent operator commands are:

```powershell
nextleap-data ingest `
  --dataset ManikaSaini/zomato-restaurant-recommendation `
  --revision 5738e9eda2fad49ad51c6e0ed26e761d9b947133 `
  --filename zomato.csv `
  --expected-sha256 4b0c91c37585310d509873dc399fdf739c7d222fcf7a693e4461b23d25a9d43d `
  --dry-run

nextleap-data ingest `
  --dataset ManikaSaini/zomato-restaurant-recommendation `
  --revision 5738e9eda2fad49ad51c6e0ed26e761d9b947133 `
  --filename zomato.csv `
  --expected-sha256 4b0c91c37585310d509873dc399fdf739c7d222fcf7a693e4461b23d25a9d43d
```

The command exits `2` when a quality gate fails. Source download, schema, decoding, and hash errors
have stable `SOURCE_*` codes. Re-running the same source name, revision, and content hash returns the
existing version without adding records or changing activation.

## Inspect and Roll Back

```powershell
nextleap-data list
nextleap-data inspect <version-uuid>
nextleap-data activate <prior-version-uuid>
```

Rollback is an ordinary atomic activation of a retained version. First inspect its quality report,
then activate it and confirm exactly one row from `nextleap-data list` has status `active`.

## Failure Recovery

1. Run `nextleap-data list` and verify the prior active version is unchanged.
2. Inspect the failed version for `gate_failures`, `rejection_reasons`, and `warning_reasons`.
3. Correct source/configuration rather than editing immutable restaurant rows.
4. Ingest a new revision or changed content. The failed version stays available for audit.

Quality thresholds are configured with the `INGESTION_*` environment variables in `.env.example`.
Production thresholds must be calibrated from a full pinned-source profile before deployment.
