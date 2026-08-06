@echo off
setlocal enabledelayedexpansion
title PC Screen Control - Setup
cd /d "%~dp0"

echo.
echo   ==========================================================
echo      PC Screen Control  -  Setup
echo   ==========================================================
echo.
echo   This registers the server with every MCP client it finds:
echo     Claude Desktop, Claude Desktop (Microsoft Store),
echo     Claude Code, and ChatGPT desktop / Codex.
echo.
echo   It will:
echo     - check that Python is installed
echo     - make sure the two Python packages are available
echo     - copy the server to your user folder
echo     - add one entry per client, each config backed up first
echo     - say per client what happened, so nothing fails quietly
echo.
echo   No administrator rights. No system settings changed.
echo   Safe to run more than once - it only overwrites its own entry.
echo.

rem -------------------------------------------------- 1. find an interpreter
rem  The py launcher is preferred: it is a real path and never the Microsoft
rem  Store placeholder that "python" on PATH often is.
set "PYEXE="
set "PYARG="
for /f "delims=" %%P in ('where py 2^>nul') do (
    if not defined PYEXE ( set "PYEXE=%%P" & set "PYARG=-3" )
)
if not defined PYEXE (
    for /f "delims=" %%P in ('where python 2^>nul') do (
        if not defined PYEXE set "PYEXE=%%P"
    )
)

if not defined PYEXE goto :nopython

rem -------------------------------------------------- 2. prove that it works
rem  Being on PATH is not the same as being able to run. The Microsoft Store
rem  placeholder is on PATH, opens the Store when executed, and runs nothing.
"%PYEXE%" %PYARG% -c "import sys; sys.exit(0 if sys.version_info[:2] >= (3,9) else 2)" >nul 2>&1
set "PRC=%ERRORLEVEL%"
rem  Verglichen wird GENAU, nicht mit "errorlevel". "if errorlevel 2" heisst
rem  in cmd "2 oder groesser" - und damit auch 9009, der Code, den Windows
rem  zurueckgibt, wenn sich das Ding auf dem PATH gar nicht starten liess.
rem  Das ist der Store-Platzhalter, also genau der Fall, den der Kommentar
rem  oben beschreibt - und er haette "your Python is too old" zu hoeren
rem  bekommen statt der Zeile, die ihm sagt, wo er Python herbekommt.
if "%PRC%"=="0" goto :python_ok
if "%PRC%"=="2" (
    echo   [X] Python is too old. Version 3.9 or newer is required.
    echo       Found: "%PYEXE%"
    goto :fail
)
goto :nopython
:python_ok

rem -------------------------------------------------- 3. find the server
rem  ONE file has to work from two places, because it is shipped in two:
rem    - inside the downloaded package, right next to server.py
rem    - in a source checkout, in scripts\ with the server one level up in src\
rem  Guessing wrong here fails with "can't open file", which reads like a
rem  broken download rather than a wrong folder. So both are checked, and if
rem  neither is there the message says which two places were looked at.
set "SRV="
if exist "%~dp0server.py"        set "SRV=%~dp0server.py"
if not defined SRV if exist "%~dp0..\src\server.py" set "SRV=%~dp0..\src\server.py"
if not defined SRV goto :noserver

rem -------------------------------------------------- 4. hand over to Python
"%PYEXE%" %PYARG% "%SRV%" --install
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
    echo   ==========================================================
    echo.
    echo      DONE  -  one thing left:
    echo.
    echo         ^>^>^>   CLOSE THE APP COMPLETELY AND START IT AGAIN   ^<^<^<
    echo.
    echo      Completely means the tray icon too, not just the window.
    echo      These apps read their config only when they start.
    echo.
    echo      Nothing else. There is no switch to flip afterwards.
    echo      To check: ask it to run  describe_screen
    echo.
    echo      Read the lines above: each client says added, updated or
    echo      skipped. "skipped" means that client is not installed here.
    echo.
    echo   ==========================================================
) else (
    echo   ==========================================================
    echo      Setup did not finish - see the messages above.
    echo   ==========================================================
)
echo.
echo   This output is also saved in install_log.txt next to the server.
echo.
pause
rem  In EINER Zeile: endlocal raeumt die Variablen weg, und %RC% wird beim
rem  Lesen der Zeile ersetzt - auf zwei Zeilen ist RC schon fort und der
rem  Rueckgabewert geht verloren. Genau den fragt jedes Skript ab, das diese
rem  Datei aufruft.
endlocal & exit /b %RC%

rem ---------------------------------------------------------------- failures
:nopython
echo.
echo   [X] No working Python was found.
echo.
echo       Install Python 3.9 or newer from python.org.
echo       During its setup, tick  "Add python.exe to PATH"  -  this is
echo       the step people miss, and without it this installer cannot
echo       find Python afterwards.
echo.
echo       Then run this file again.
echo.
echo   Opening the download page ...
start "" "https://www.python.org/downloads/"
goto :fail

:noserver
echo.
echo   [X] server.py was not found. Looked in:
echo         %~dp0server.py
echo         %~dp0..\src\server.py
echo.
echo       If you extracted the download, run this file from INSIDE the
echo       extracted folder - not from within the ZIP viewer, which hands
echo       out a temporary copy without the rest of the files.
echo.
goto :fail

:fail
echo.
pause
endlocal & exit /b 1
