@echo off
setlocal
title Gayanara SQL Practice Lab Backend

set "PROJECT_DIR=%~dp0"

if not exist "%PROJECT_DIR%server.py" (
    echo ERROR: server.py tidak ditemukan di folder yang sama dengan file BAT.
    echo Folder yang diperiksa:
    echo %PROJECT_DIR%
    echo.
    echo Simpan file BAT ini di folder sql_practice_lab bersama server.py.
    pause
    exit /b 1
)

cd /d "%PROJECT_DIR%"
if errorlevel 1 (
    echo ERROR: Tidak dapat membuka folder proyek.
    pause
    exit /b 1
)

echo ==========================================
echo   Gayanara SQL Practice Lab Backend
echo ==========================================
echo Folder: %PROJECT_DIR%
echo.
echo Masukkan password PostgreSQL saat diminta.
echo Input password tidak akan ditampilkan.
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$secure = Read-Host 'Password PostgreSQL' -AsSecureString; " ^
  "$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure); " ^
  "try { " ^
  "  $env:GAYANARA_DB_PASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr); " ^
  "  python server.py; " ^
  "} finally { " ^
  "  if ($ptr -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }; " ^
  "  Remove-Item Env:GAYANARA_DB_PASSWORD -ErrorAction SilentlyContinue; " ^
  "}"

echo.
echo Backend telah berhenti atau gagal dijalankan.
pause
endlocal
