@echo off
REM Batch script to run all tests
REM Uruchomienie z folderu aifx: tests\run_all_tests.bat
REM Uruchomienie z folderu tests: run_all_tests.bat

echo ================================================================================
echo URUCHAMIAM WSZYSTKIE TESTY - Support Breakout Strategy
echo ================================================================================
echo.

set TOTAL=0
set PASSED=0
set FAILED=0

echo --------------------------------------------------------------------------------
echo TEST 1/8: Close At EOD (5 testow)
echo --------------------------------------------------------------------------------
python test_close_at_eod.py
if %ERRORLEVEL% EQU 0 (
    echo PASSED
    set /A PASSED+=1
) else (
    echo FAILED
    set /A FAILED+=1
)
set /A TOTAL+=1
echo.

echo --------------------------------------------------------------------------------
echo TEST 2/8: Min Slope (2 testy)
echo --------------------------------------------------------------------------------
python test_min_slope.py
if %ERRORLEVEL% EQU 0 (
    echo PASSED
    set /A PASSED+=1
) else (
    echo FAILED
    set /A FAILED+=1
)
set /A TOTAL+=1
echo.

echo --------------------------------------------------------------------------------
echo TEST 3/8: Min Slope Integration (1 test)
echo --------------------------------------------------------------------------------
python test_min_slope_integration.py
if %ERRORLEVEL% EQU 0 (
    echo PASSED
    set /A PASSED+=1
) else (
    echo FAILED
    set /A FAILED+=1
)
set /A TOTAL+=1
echo.

echo --------------------------------------------------------------------------------
echo TEST 4/8: Support Strategy (6 testow)
echo --------------------------------------------------------------------------------
python test_support_strategy.py
if %ERRORLEVEL% EQU 0 (
    echo PASSED
    set /A PASSED+=1
) else (
    echo FAILED
    set /A FAILED+=1
)
set /A TOTAL+=1
echo.

echo --------------------------------------------------------------------------------
echo TEST 5/8: Short Positions (5 testow)
echo --------------------------------------------------------------------------------
python test_short_positions.py
if %ERRORLEVEL% EQU 0 (
    echo PASSED
    set /A PASSED+=1
) else (
    echo FAILED
    set /A FAILED+=1
)
set /A TOTAL+=1
echo.

echo --------------------------------------------------------------------------------
echo TEST 6/8: Legend (2 testy)
echo --------------------------------------------------------------------------------
python test_legend.py
if %ERRORLEVEL% EQU 0 (
    echo PASSED
    set /A PASSED+=1
) else (
    echo FAILED
    set /A FAILED+=1
)
set /A TOTAL+=1
echo.

echo --------------------------------------------------------------------------------
echo TEST 7/8: Hierarchical Lines (1 test)
echo --------------------------------------------------------------------------------
python test_hierarchical.py
if %ERRORLEVEL% EQU 0 (
    echo PASSED
    set /A PASSED+=1
) else (
    echo FAILED
    set /A FAILED+=1
)
set /A TOTAL+=1
echo.

echo --------------------------------------------------------------------------------
echo TEST 8/8: Ascending/Descending (3 testy)
echo --------------------------------------------------------------------------------
python test_ascending_descending.py
if %ERRORLEVEL% EQU 0 (
    echo PASSED
    set /A PASSED+=1
) else (
    echo FAILED
    set /A FAILED+=1
)
set /A TOTAL+=1
echo.

echo ================================================================================
echo PODSUMOWANIE
echo ================================================================================
echo Calkowita liczba modulow testowych: %TOTAL%
echo Przeszly: %PASSED%
echo Nie przeszly: %FAILED%
echo ================================================================================

if %FAILED% EQU 0 (
    echo Wszystkie testy przeszly!
    exit /b 0
) else (
    echo Niektore testy nie przeszly
    exit /b 1
)
