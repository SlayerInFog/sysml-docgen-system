$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$workspace = (Resolve-Path (Join-Path $scriptDir "..")).Path
$workspaceParent = Split-Path -Parent $workspace
$jupyterRoot = Join-Path $workspace ".jupyter-work"
$runId = Get-Random -Minimum 100000 -Maximum 999999

$jupyterCandidates = @(
  (Join-Path $workspace ".venv\Scripts\jupyter-lab.exe"),
  (Join-Path $workspace "jupyter-env\Scripts\jupyter-lab.exe"),
  (Join-Path $workspaceParent "jupyter-env\Scripts\jupyter-lab.exe")
)
$jupyterLab = $jupyterCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $jupyterLab) {
  $jupyterLab = "jupyter-lab"
}

New-Item -ItemType Directory -Force -Path `
  "$jupyterRoot\config", `
  "$jupyterRoot\data", `
  "$jupyterRoot\runtime-$runId", `
  "$jupyterRoot\ipython" | Out-Null

$env:JUPYTER_CONFIG_DIR = "$jupyterRoot\config"
$env:JUPYTER_DATA_DIR = "$jupyterRoot\data"
$env:JUPYTER_RUNTIME_DIR = "$jupyterRoot\runtime-$runId"
$env:IPYTHONDIR = "$jupyterRoot\ipython"
$env:SYSML_DOCGEN_WORKSPACE = $workspace

Set-Location -LiteralPath $workspace

Write-Host ""
Write-Host "JupyterLab is starting..." -ForegroundColor Cyan
Write-Host "Keep this PowerShell window open while using Jupyter." -ForegroundColor Yellow
Write-Host "Workspace: $workspace" -ForegroundColor DarkGray
Write-Host "Open this URL in your browser:" -ForegroundColor Green
Write-Host "http://127.0.0.1:8888/lab/tree/notebooks/sysml_docgen_openmbee_demo.ipynb" -ForegroundColor Green
Write-Host ""

& $jupyterLab `
  "--notebook-dir=$workspace" `
  "notebooks/sysml_docgen_openmbee_demo.ipynb" `
  "--ip=127.0.0.1" `
  "--port=8888" `
  "--no-browser" `
  "--ServerApp.use_redirect_file=False" `
  "--ServerApp.token=" `
  "--ServerApp.password="
