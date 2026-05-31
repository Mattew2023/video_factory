@echo off
setlocal

set "SCRIPT=%~dp0douyin_merge_compress_tool.py"
set "CODEX_PYTHONW=C:\Users\27110\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\pythonw.exe"
set "CODEX_PYTHON=C:\Users\27110\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

if not exist "%SCRIPT%" (
    echo Missing script:
    echo %SCRIPT%
    pause
    exit /b 1
)

if exist "%CODEX_PYTHONW%" (
    start "" "%CODEX_PYTHONW%" "%SCRIPT%"
    exit /b 0
)

if exist "%CODEX_PYTHON%" (
    start "" "%CODEX_PYTHON%" "%SCRIPT%"
    exit /b 0
)

where pythonw >nul 2>nul
if not errorlevel 1 (
    start "" pythonw "%SCRIPT%"
    exit /b 0
)

where python >nul 2>nul
if not errorlevel 1 (
    start "" python "%SCRIPT%"
    exit /b 0
)

where py >nul 2>nul
if not errorlevel 1 (
    start "" py -3 "%SCRIPT%"
    exit /b 0
)

echo Python was not found.
echo Please install Python 3 or check the bundled Codex Python path.
pause
exit /b 1
