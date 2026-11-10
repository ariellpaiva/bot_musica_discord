@echo off
rem Liga o bipbip. Fecha esta janela pra desligar o bot.
rem Se cair (ex.: sem internet), tenta de novo em 15s.
title bipbip
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
:loop
"%LOCALAPPDATA%\Programs\Python\Python313\python.exe" bot.py
if %errorlevel%==3 (
    echo.
    pause
    exit /b
)
echo.
echo Bot caiu. Tentando de novo em 15s (fecha a janela pra desligar)...
timeout /t 15 /nobreak > nul
goto loop
