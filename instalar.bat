@echo off
rem Instala tudo que o bipbip precisa num PC novo (Windows 10/11).
rem Pode rodar mais de uma vez: o que já estiver instalado é pulado.
chcp 65001 > nul
title Instalando o bipbip
cd /d "%~dp0"

set WINGET=winget install -e --silent --accept-package-agreements --accept-source-agreements --id
set PYTHON="%LOCALAPPDATA%\Programs\Python\Python313\python.exe"

echo.
echo [1/6] Visual C++ (runtime da Microsoft, o ffmpeg e o Python precisam dele)
%WINGET% Microsoft.VCRedist.2015+.x64

echo.
echo [2/6] Visual Studio Build Tools (compilador C++, alguns pacotes do pip precisam)
echo       Esse é grande (alguns GB) e demora. Pode aparecer a janela do instalador.
%WINGET% Microsoft.VisualStudio.2022.BuildTools --override "--wait --passive --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"

echo.
echo [3/6] Python 3.13
%WINGET% Python.Python.3.13 --scope user

echo.
echo [4/6] ffmpeg
%WINGET% Gyan.FFmpeg

echo.
echo [5/6] App do Spotify
%WINGET% Spotify.Spotify

echo.
echo [6/6] Bibliotecas Python (requirements.txt)
if not exist %PYTHON% (
    echo ERRO: Python não encontrado em %PYTHON%
    echo Fecha esta janela, abre de novo e roda o instalar.bat outra vez.
    pause
    exit /b 1
)
%PYTHON% -m pip install --upgrade pip
%PYTHON% -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo ERRO ao instalar as bibliotecas. Reinicia o PC e roda o instalar.bat de novo.
    pause
    exit /b 1
)

if not exist .env (
    copy .env.example .env > nul
    echo.
    echo Criei o arquivo .env. Abre ele e coloca os tokens ^(ver README.txt, passo 4^).
)

echo.
echo ============================================================
echo  Pronto! Agora falta fazer na mão:
echo   1. Instalar o VB-Cable: https://vb-audio.com/Cable/ e REINICIAR o PC
echo   2. Abrir o Spotify e fazer login
echo   3. Configurações - Som - Mixer de volume - Spotify: saída = CABLE Input
echo   4. Preencher os tokens no .env
echo   Depois é só dar dois cliques no iniciar.bat
echo ============================================================
pause
