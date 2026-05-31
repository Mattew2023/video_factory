@echo off
setlocal
cd /d "%~dp0"
set "PORT=10809"
set "NODE_EXE="

for /f "delims=" %%I in ('where node 2^>nul') do (
  if not defined NODE_EXE set "NODE_EXE=%%I"
)

if not defined NODE_EXE (
  if exist "D:\Program Files\nodejs\node.exe" (
    set "NODE_EXE=D:\Program Files\nodejs\node.exe"
  ) else (
    echo Node.js was not found. Please install Node.js or update NODE_EXE in this file.
    pause
    exit /b 1
  )
)

netstat -ano | findstr /R /C:":%PORT% .*LISTENING" >nul
if errorlevel 1 (
  start "" /D "%~dp0" /MIN "%NODE_EXE%" serve-local.mjs %PORT%
  timeout /t 1 /nobreak >nul
)

start "" "http://127.0.0.1:%PORT%/admin"
