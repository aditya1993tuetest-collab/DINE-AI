$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true

Write-Host "Checking API"
python -m ruff check apps/api
python -m ruff format --check apps/api
python -m mypy apps/api/src apps/api/tests
python -m pytest apps/api/tests

Write-Host "Checking web application"
Push-Location apps/web
try {
    npm run format:check
    npm run lint
    npm run typecheck
    npm test
    npm run build
}
finally {
    Pop-Location
}
