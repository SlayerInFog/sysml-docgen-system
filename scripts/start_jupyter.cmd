@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "WORKSPACE=%%~fI"
for %%I in ("%WORKSPACE%\..") do set "WORKSPACE_PARENT=%%~fI"
set "JUPYTER_ROOT=%WORKSPACE%\.jupyter-work"
set "JUPYTER_RUN_ID=%RANDOM%%RANDOM%"
set "JUPYTER_LAB=jupyter-lab"

if exist "%WORKSPACE%\.venv\Scripts\jupyter-lab.exe" set "JUPYTER_LAB=%WORKSPACE%\.venv\Scripts\jupyter-lab.exe"
if exist "%WORKSPACE%\jupyter-env\Scripts\jupyter-lab.exe" set "JUPYTER_LAB=%WORKSPACE%\jupyter-env\Scripts\jupyter-lab.exe"
if exist "%WORKSPACE_PARENT%\jupyter-env\Scripts\jupyter-lab.exe" set "JUPYTER_LAB=%WORKSPACE_PARENT%\jupyter-env\Scripts\jupyter-lab.exe"

if not exist "%JUPYTER_ROOT%\config" mkdir "%JUPYTER_ROOT%\config"
if not exist "%JUPYTER_ROOT%\data" mkdir "%JUPYTER_ROOT%\data"
if not exist "%JUPYTER_ROOT%\runtime-%JUPYTER_RUN_ID%" mkdir "%JUPYTER_ROOT%\runtime-%JUPYTER_RUN_ID%"
if not exist "%JUPYTER_ROOT%\ipython" mkdir "%JUPYTER_ROOT%\ipython"

set "JUPYTER_CONFIG_DIR=%JUPYTER_ROOT%\config"
set "JUPYTER_DATA_DIR=%JUPYTER_ROOT%\data"
set "JUPYTER_RUNTIME_DIR=%JUPYTER_ROOT%\runtime-%JUPYTER_RUN_ID%"
set "IPYTHONDIR=%JUPYTER_ROOT%\ipython"
set "SYSML_DOCGEN_WORKSPACE=%WORKSPACE%"

cd /d "%WORKSPACE%"

echo.
echo JupyterLab is starting...
echo Keep this window open while using Jupyter.
echo Workspace: %WORKSPACE%
echo Open this URL in your browser:
echo http://127.0.0.1:8888/lab/tree/notebooks/sysml_docgen_openmbee_demo.ipynb
echo.
echo Startup log: %JUPYTER_ROOT%\jupyter-window.log
echo.

"%JUPYTER_LAB%" --notebook-dir="%WORKSPACE%" notebooks/sysml_docgen_openmbee_demo.ipynb --ip=127.0.0.1 --port=8888 --no-browser --ServerApp.use_redirect_file=False --ServerApp.token= --ServerApp.password= > "%JUPYTER_ROOT%\jupyter-window.log" 2>&1

echo.
echo JupyterLab exited. Press any key to close this window.
pause >nul
