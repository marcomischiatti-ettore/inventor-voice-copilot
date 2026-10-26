@echo off
title Autodesk Inventor Copilot
echo Avvio di Autodesk Inventor Copilot in corso...
cd /d "%~dp0"
python copilot_gui.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Si e verificato un errore durante l'avvio. Premi un tasto per visualizzare i dettagli.
    pause
)
