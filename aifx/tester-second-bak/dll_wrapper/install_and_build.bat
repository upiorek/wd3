@echo off
echo ============================================================
echo Installing Python 3.11 (32-bit) for DLL compilation
echo ============================================================
echo.

set INSTALL_DIR=C:\Python311-32
set INSTALLER=python-3.11.9.exe
set DOWNLOAD_URL=https://www.python.org/ftp/python/3.11.9/python-3.11.9.exe

REM Check if already installed
if exist "%INSTALL_DIR%\python.exe" (
    echo Python 3.11 32-bit already installed at: %INSTALL_DIR%
    goto :build
)

echo Downloading Python 3.11.9 32-bit installer...
powershell -Command "Invoke-WebRequest -Uri '%DOWNLOAD_URL%' -OutFile '%INSTALLER%'"

if not exist "%INSTALLER%" (
    echo ERROR: Download failed
    exit /b 1
)

echo.
echo Installing Python 3.11 32-bit to: %INSTALL_DIR%
echo This will install silently with all features...
echo.

REM Install Python silently
%INSTALLER% /quiet InstallAllUsers=1 PrependPath=0 Include_test=0 ^
    TargetDir=%INSTALL_DIR% ^
    Include_pip=1 ^
    Include_dev=1 ^
    Include_lib=1

echo Waiting for installation to complete...
timeout /t 30 /nobreak > nul

if not exist "%INSTALL_DIR%\python.exe" (
    echo ERROR: Installation failed
    exit /b 1
)

echo.
echo ✓ Python 3.11 32-bit installed successfully
echo.

REM Clean up installer
del "%INSTALLER%" 2>nul

:build
echo ============================================================
echo Building PythonAnalyzer.dll with Python 3.11 32-bit
echo ============================================================
echo.

REM Update build script
call build_dll_311.bat

