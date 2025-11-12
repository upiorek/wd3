@echo off
REM Uruchamia wszystkie testy z poprawnym kodowaniem UTF-8

echo.
echo ################################################################################
echo # URUCHAMIAM WSZYSTKIE TESTY
echo ################################################################################
echo.

set PYTHONIOENCODING=utf-8

echo Uruchamiam test_strategy.py...
python test_strategy.py
if %ERRORLEVEL% NEQ 0 (
    echo [FAILED] test_strategy.py
    set TEST_FAILED=1
) else (
    echo [PASSED] test_strategy.py
)

echo.
echo Uruchamiam test_support_strategy.py...
python test_support_strategy.py
if %ERRORLEVEL% NEQ 0 (
    echo [FAILED] test_support_strategy.py
    set TEST_FAILED=1
) else (
    echo [PASSED] test_support_strategy.py
)

echo.
echo Uruchamiam impulse_detector.py --test...
python ..\impulse_detector.py --test
if %ERRORLEVEL% NEQ 0 (
    echo [FAILED] impulse_detector.py --test
    set TEST_FAILED=1
) else (
    echo [PASSED] impulse_detector.py --test
)

echo.
echo ################################################################################
if defined TEST_FAILED (
    echo # NIEKTORE TESTY FAILED
    echo ################################################################################
    exit /b 1
) else (
    echo # WSZYSTKIE TESTY PASSED
    echo ################################################################################
    exit /b 0
)
