@echo off
rem Liga o bipbip. Fecha esta janela pra desligar o bot.
rem Se cair (ex.: sem internet), tenta de novo em 15s.
title bipbip
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
rem Abre o app do Spotify (se já estiver aberto, só traz pra frente)
start "" spotify:
rem O YouTube muda direto: atualiza o yt-dlp em silêncio antes de ligar
echo Atualizando yt-dlp...
"%LOCALAPPDATA%\Programs\Python\Python313\python.exe" -m pip install -q -U "yt-dlp[default]" > nul 2>&1
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
