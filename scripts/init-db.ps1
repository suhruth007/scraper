param(
    [string]$EnvName = "ai-job-scraper"
)

# Activate conda env
Write-Host "Activating conda env: $EnvName"
& conda activate $EnvName

# Set Flask env vars
$env:FLASK_APP = "src/app"
$env:FLASK_ENV = "development"

# Initialize migration folder if missing
if (-not (Test-Path -Path ".\migrations")) {
    Write-Host 'migrations folder not found. Running: flask db init'
    flask db init
} else {
    Write-Host 'migrations folder exists — skipping flask db init'
}

Write-Host 'Running: flask db migrate -m "init"'
flask db migrate -m "init"

Write-Host 'Running: flask db upgrade'
flask db upgrade

Write-Host 'Database migration complete.'
