@echo off
setlocal EnableExtensions

set "SCRIPT=%~dp0video_compressor_tool.py"
set "LOG=%~dp0video_compressor_startup.log"
set "BUNDLED_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

if not exist "%SCRIPT%" (
    echo Missing script:
    echo %SCRIPT%
    pause
    exit /b 1
)

call :try_python_command python
if not errorlevel 1 exit /b 0

call :try_py_launcher
if not errorlevel 1 exit /b 0

if exist "%BUNDLED_PYTHON%" (
    call :try_python_exe "%BUNDLED_PYTHON%"
    if not errorlevel 1 exit /b 0
)

echo No usable Python with Tkinter was found.
echo.
echo Please install the official Python 3 from python.org,
echo and make sure Tcl/Tk and IDLE are included.
echo.
echo Last error log:
echo %LOG%
pause
exit /b 1

:try_python_command
where %~1 >nul 2>nul
if errorlevel 1 exit /b 1
%~1 -c "import tkinter as tk; root=tk.Tk(); root.withdraw(); root.destroy()" >nul 2>"%LOG%"
if errorlevel 1 exit /b 1
%~1 "%SCRIPT%"
if errorlevel 1 pause
exit /b %errorlevel%

:try_py_launcher
where py >nul 2>nul
if errorlevel 1 exit /b 1
py -3 -c "import tkinter as tk; root=tk.Tk(); root.withdraw(); root.destroy()" >nul 2>"%LOG%"
if errorlevel 1 exit /b 1
py -3 "%SCRIPT%"
if errorlevel 1 pause
exit /b %errorlevel%

:try_python_exe
%~1 -c "import tkinter as tk; root=tk.Tk(); root.withdraw(); root.destroy()" >nul 2>"%LOG%"
if errorlevel 1 exit /b 1
%~1 "%SCRIPT%"
if errorlevel 1 pause
exit /b %errorlevel%
