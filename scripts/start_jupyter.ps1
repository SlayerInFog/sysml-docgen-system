$ErrorActionPreference = "Stop"

$workspace = "E:\sysml\sysml-docgen-system"
$jupyterRoot = "E:\sysml\jupyter-work"
$runId = Get-Random -Minimum 100000 -Maximum 999999

New-Item -ItemType Directory -Force -Path `
  "$jupyterRoot\config", `
  "$jupyterRoot\data", `
  "$jupyterRoot\runtime-$runId", `
  "$jupyterRoot\ipython" | Out-Null

$env:JUPYTER_CONFIG_DIR = "$jupyterRoot\config"
$env:JUPYTER_DATA_DIR = "$jupyterRoot\data"
$env:JUPYTER_RUNTIME_DIR = "$jupyterRoot\runtime-$runId"
$env:IPYTHONDIR = "$jupyterRoot\ipython"

Set-Location -LiteralPath $workspace

Write-Host ""
Write-Host "JupyterLab is starting..." -ForegroundColor Cyan
Write-Host "Keep this PowerShell window open while using Jupyter." -ForegroundColor Yellow
Write-Host "Open this URL in your browser:" -ForegroundColor Green
Write-Host "http://127.0.0.1:8888/lab/tree/sysml_docgen_openmbee_demo.ipynb" -ForegroundColor Green
Write-Host ""

& "E:\sysml\jupyter-env\Scripts\jupyter-lab.exe" `
  "notebooks" `
  "--ip=127.0.0.1" `
  "--port=8888" `
  "--no-browser" `
  "--ServerApp.use_redirect_file=False" `
  "--ServerApp.token=" `
  "--ServerApp.password="
