@echo off
echo ============================================================
echo Building C++ Test for PythonAnalyzer.dll
echo ============================================================
echo.

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
echo.

REM Setup Visual Studio environment for x86
call "%VS_PATH%\VC\Auxiliary\Build\vcvars32.bat"

echo.
echo ============================================================
echo Compiling test_dll.cpp...
echo ============================================================
echo.

REM Compile the test program (32-bit to match the DLL)
cl.exe /EHsc /W3 test_dll.cpp /Fe:test_dll.exe

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

REM Clean up intermediate files
del *.obj 2>nul

echo Running test...
echo.
echo ============================================================
echo.

REM Run the test
test_dll.exe

echo.
echo ============================================================
echo Test completed
echo ============================================================
echo.
echo Check PythonAnalyzer.log for detailed logging output
echo.
