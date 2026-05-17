@echo off
chcp 65001 >nul
setlocal EnableExtensions
title TypeBuddy
REM One instance + Administrator for global keyboard hook.

cd /d "%~dp0"

net session >nul 2>&1
if errorlevel 1 (
  echo TypeBuddy needs Administrator for system-wide keyboard hook.
  echo Requesting UAC...
  powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -WorkingDirectory '%~dp0.' -Verb RunAs"
  exit /b 0
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0TYPEBUDDY_ONCE.ps1"
if errorlevel 1 (
  echo.
  pause
  exit /b 1
)

echo Done. Look for the TypeBuddy strip at the top of your screen.
timeout /t 4 >nul
exit /b 0
