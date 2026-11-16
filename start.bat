@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"
title Shot2Key (BE + FE)

echo ============================================
echo   Shot2Key - Setup ^& Launcher
echo ============================================
echo.

:: ---------------------------------------------------------------------------
:: 1. Required agent CLIs (agy / codex)
::    Default: both. Override with:  set SHOT2KEY_REQUIRE_CLI=agy
::    (set it to a single space to skip the check entirely)
:: ---------------------------------------------------------------------------
set "REQ=%SHOT2KEY_REQUIRE_CLI%"
if not defined REQ set "REQ=agy,codex"

set "MISSING="
if not "%REQ%"==" " (
    for %%C in (%REQ:,= %) do (
        where %%C >nul 2>&1
        if errorlevel 1 set "MISSING=!MISSING! %%C"
    )
)

if not "!MISSING!"=="" (
    echo [ERROR] CLI wajib belum terpasang:!MISSING!
    echo.
    echo   Antigravity CLI ^(agy^)
    echo     Windows PowerShell : irm https://antigravity.google/cli/install.ps1 ^| iex
    echo     Docs               : https://antigravity.google/docs/cli/reference
    echo.
    echo   OpenAI Codex CLI ^(codex^)
    echo     NPM                : npm install -g @openai/codex@latest
    echo     Repo               : https://github.com/openai/codex
    echo.
    echo   Setelah terpasang, tutup dan buka lagi terminal ini ^(PATH perlu di-refresh^),
    echo   lalu jalankan start.bat kembali.
    echo.
    echo   Ingin melewati pengecekan ini?  set SHOT2KEY_REQUIRE_CLI=agy
    echo.
    pause
    exit /b 1
)

:: ---------------------------------------------------------------------------
:: 2. Python
:: ---------------------------------------------------------------------------
set "PY_CMD="
py -3.12 -c "import sys" >nul 2>&1 && set "PY_CMD=py -3.12"
if not defined PY_CMD (
    py -3.11 -c "import sys" >nul 2>&1 && set "PY_CMD=py -3.11"
)
if not defined PY_CMD (
    py -3 -c "import sys" >nul 2>&1 && set "PY_CMD=py -3"
)
if not defined PY_CMD (
    where python >nul 2>&1 && set "PY_CMD=python"
)

if not defined PY_CMD (
    echo [ERROR] Python 3.10+ tidak ditemukan di PATH.
    echo Silakan install dari https://www.python.org/downloads/
    pause
    exit /b 1
)

:: ---------------------------------------------------------------------------
:: 3. Node.js / npm
:: ---------------------------------------------------------------------------
where npm.cmd >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js / npm tidak ditemukan di PATH.
    echo Silakan install Node.js 18+ dari https://nodejs.org/
    pause
    exit /b 1
)

:: ---------------------------------------------------------------------------
:: 4. Hand over to launcher.py: venv, requirements, npm install, ffmpeg, servers
:: ---------------------------------------------------------------------------
echo [1/2] Memeriksa Python, Node.js, dan CLI... OK
echo [2/2] Menyiapkan .venv, dependensi, lalu menjalankan server...
echo.

%PY_CMD% "%ROOT_DIR%launcher.py"
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
    echo.
    echo [ERROR] Launcher berhenti dengan kode %EXIT_CODE%.
    pause
)

endlocal & exit /b %EXIT_CODE%
