@echo off
setlocal EnableExtensions

echo ============================================
echo   Shot2Key - Stopping Servers
echo ============================================
echo.

set "STOPPED=0"

:: 1. Backend (FastAPI / uvicorn) on port 8000
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":8000 .*LISTENING"') do (
    if not "%%P"=="0" (
        echo Menghentikan Backend ^(PID %%P, port 8000^)...
        taskkill /PID %%P /T /F >nul 2>&1
        set "STOPPED=1"
    )
)

:: 2. Frontend (Vite) on port 5173
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":5173 .*LISTENING"') do (
    if not "%%P"=="0" (
        echo Menghentikan Frontend ^(PID %%P, port 5173^)...
        taskkill /PID %%P /T /F >nul 2>&1
        set "STOPPED=1"
    )
)

:: 3. Launcher window, if still open
taskkill /FI "WINDOWTITLE eq Shot2Key (BE + FE)*" /F >nul 2>&1

if "%STOPPED%"=="0" (
    echo Tidak ada server Shot2Key yang berjalan di port 8000 / 5173.
) else (
    echo.
    echo Semua server Shot2Key berhasil dihentikan.
)

ping -n 3 127.0.0.1 >nul
endlocal
