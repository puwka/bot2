# Create .venv from Python 3.11 or 3.12 (no downloads)
$needle = @('3.12', '3.11')
$found = $null
foreach ($v in $needle) {
    $null = & py -$v -c "import sys" 2>$null
    if ($LASTEXITCODE -eq 0) {
        $found = $v
        break
    }
}
if (-not $found) {
    Write-Host 'Python 3.11 or 3.12 not found. Install one from python.org or Microsoft Store.' -ForegroundColor Red
    exit 1
}
if (Test-Path .venv) {
    Remove-Item -Recurse -Force .venv
}
Write-Host "Creating .venv with Python $found..."
& py -$found -m venv .venv
if ($LASTEXITCODE -ne 0) {
    Write-Host 'Failed to create venv.' -ForegroundColor Red
    exit 1
}
Write-Host 'Installing dependencies (using venv pip)...' -ForegroundColor Green
& .\.venv\Scripts\pip.exe install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host 'pip install failed.' -ForegroundColor Red
    exit 1
}
Write-Host 'Done. Next run:' -ForegroundColor Green
Write-Host '  .\.venv\Scripts\Activate.ps1' -ForegroundColor Cyan
Write-Host '  python -m app.main' -ForegroundColor Cyan
