@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0ani-cli-ru.ps1" %*
