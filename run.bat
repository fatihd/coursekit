@echo off
setlocal
set "ROOT=%~dp0"
set "IMAGE=lang-research-local-study"
set "PORT=%PORT%"
if "%PORT%"=="" set "PORT=8787"

docker build --tag "%IMAGE%" "%ROOT%"
if errorlevel 1 exit /b %errorlevel%

echo Course will be available at http://127.0.0.1:%PORT%/app/index.html
start "" "http://127.0.0.1:%PORT%/app/index.html"
docker run --rm -it -p 127.0.0.1:%PORT%:8000 -v "%ROOT%:/course:ro" "%IMAGE%"
