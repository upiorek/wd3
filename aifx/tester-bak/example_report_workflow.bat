@echo off
REM ============================================================================
REM MT4 Test Report Generation - Example Workflow
REM ============================================================================
REM This script demonstrates how to run MT4 tests and generate reports
REM
REM Usage: Run this batch file from the tester directory
REM ============================================================================

echo.
echo ============================================================================
echo MT4 AUTOMATED TESTING WITH REPORT GENERATION
echo ============================================================================
echo.
echo This example will:
echo   1. Run an MT4 backtest for 2025-11-12
echo   2. Wait for the test to complete
echo   3. Automatically generate and save a formatted report
echo.
echo Press any key to start the test, or Ctrl+C to cancel...
pause >nul

echo.
echo ----------------------------------------------------------------------------
echo STEP 1: Launching MT4 Test
echo ----------------------------------------------------------------------------
echo Running: python mt4_tester.py --date 2025-11-12 --shutdown --wait
echo.

python mt4_tester.py --date 2025-11-12 --shutdown --wait

echo.
echo ----------------------------------------------------------------------------
echo TEST COMPLETE
echo ----------------------------------------------------------------------------
echo.
echo Check the current directory for the generated report file:
echo   mt4_test_report_YYYYMMDD_HHMMSS.txt
echo.
echo You can also view the HTML report from MT4:
echo   AppData\Roaming\MetaQuotes\Terminal\...\tester\reports\
echo.
echo Press any key to exit...
pause >nul
