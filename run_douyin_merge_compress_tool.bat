@echo off
setlocal

set "SCRIPT=%~dp0douyin_merge_compress_tool.py"

if not exist "%SCRIPT%" (
    echo Missing script:
    echo %SCRIPT%
    pause
    exit /b 1
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
echo Please install Python 3 or package this tool as an exe before sharing it.
pause
exit /b 1
