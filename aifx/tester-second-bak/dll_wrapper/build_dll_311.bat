@echo off
echo ============================================================
echo Building PythonAnalyzer.dll (32-bit) with Python 3.11
echo ============================================================
echo.

REM Set Python 3.11 32-bit paths
set PYTHON_PATH=C:\Python311-32
set PYTHON_INCLUDE=%PYTHON_PATH%\include
set PYTHON_LIBS=%PYTHON_PATH%\libs

REM Check if Python 3.11 32-bit exists
if not exist "%PYTHON_PATH%\python.exe" (
    echo ERROR: Python 3.11 32-bit not found at: %PYTHON_PATH%
    echo Please run install_and_build.bat first
    exit /b 1
)

REM Visual Studio 2022 paths
set VSWHERE="%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
for /f "usebackq tokens=*" %%i in (`%VSWHERE% -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do (
  set VS_PATH=%%i
)

if not defined VS_PATH (
    echo ERROR: Visual Studio 2022 not found
    exit /b 1
)

echo Found Visual Studio at: %VS_PATH%
echo Python 3.11 32-bit path: %PYTHON_PATH%
echo.

REM Setup Visual Studio environment for x86
call "%VS_PATH%\VC\Auxiliary\Build\vcvars32.bat"

echo.
echo ============================================================
echo Compiling PythonAnalyzer.cpp...
echo ============================================================
echo.

REM Compile the DLL (32-bit)
cl.exe /LD ^
    /D_USRDLL /D_WINDLL /DWIN32 ^
    /EHsc ^
    /I"%PYTHON_INCLUDE%" ^
    PythonAnalyzer.cpp ^
    /link ^
    /LIBPATH:"%PYTHON_LIBS%" ^
    python311.lib ^
    /OUT:PythonAnalyzer.dll ^
    /MACHINE:X86

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ============================================================
    echo BUILD FAILED
    echo ============================================================
    exit /b 1
)

echo.
echo ============================================================
echo BUILD SUCCESSFUL
echo ============================================================
echo.
echo DLL created: PythonAnalyzer.dll
echo Python runtime required: python311.dll (from %PYTHON_PATH%)
echo.

REM Clean up intermediate files
del *.obj *.exp 2>nul

echo [SUCCESS] Ready to deploy!
echo.
echo Next steps:
echo 1. Copy PythonAnalyzer.dll to MT4 Libraries folder
echo 2. Ensure python311.dll is accessible (add %PYTHON_PATH% to PATH or copy DLL)
echo 3. Run: python cleanup.py
echo 4. Run: python run_strategy_tester.py
echo.
