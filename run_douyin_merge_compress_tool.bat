@echo off
setlocal

set "SCRIPT=%~dp0douyin_merge_compress_tool.py"
set "BUNDLED_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

if not exist "%SCRIPT%" (
    echo Missing script:
    echo %SCRIPT%
    pause
    exit /b 1
)

if exist "%BUNDLED_PYTHON%" (
    "%BUNDLED_PYTHON%" "%SCRIPT%"
    if errorlevel 1 pause
    exit /b %errorlevel%
)

where python >nul 2>nul
if not errorlevel 1 (
    python "%SCRIPT%"
    if errorlevel 1 pause
    exit /b %errorlevel%
)

where py >nul 2>nul
if not errorlevel 1 (
    py -3 -c "import tkinter" >nul 2>nul
    if not errorlevel 1 (
        py -3 "%SCRIPT%"
        if errorlevel 1 pause
        exit /b %errorlevel%
    )
)

echo Python was not found.
echo Please install Python 3, or package this tool as an exe before sharing it.
pause
exit /b 1
