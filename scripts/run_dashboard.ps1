param(
  [string]$BindAddress = "127.0.0.1",
  [int]$Port = 8000
)

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot
uv run uvicorn opportunity.web:app --host $BindAddress --port $Port
