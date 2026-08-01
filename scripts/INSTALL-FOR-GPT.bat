@echo off
rem ===================================================================
rem  PC Screen Control - Setup fuer ChatGPT Desktop / Codex
rem
rem  Doppelklicken. Das war es.
rem
rem  Traegt den Server neben dieser Datei in ~/.codex/config.toml ein,
rem  nachdem geprueft wurde, dass er wirklich antwortet. Deine anderen
rem  Einstellungen bleiben unangetastet, eine Sicherung wird angelegt.
rem ===================================================================
setlocal
cd /d "%~dp0"

where py >nul 2>&1 && (set "PY=py -3") || (set "PY=python")
%PY% --version >nul 2>&1
if errorlevel 1 (
  echo.
  echo   Python wurde nicht gefunden.
  echo   Hole es von https://www.python.org/downloads/ und setze beim
  echo   Installieren den Haken bei "Add python.exe to PATH".
  echo.
  pause
  exit /b 1
)

%PY% "%~dp0install-for-gpt.py" "%~dp0"
echo.
pause
endlocal
