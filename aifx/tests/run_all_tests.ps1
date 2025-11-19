# PowerShell script to run all tests
# Uruchomienie z folderu aifx: .\tests\run_all_tests.ps1

# Zapamietaj biezacy katalog
$originalDir = Get-Location

# Przejdz do folderu aifx (parent tests jesli jestesmy w tests)
if ((Get-Location).Path -match '\\tests$') {
    Set-Location ..
}

$aifxDir = Get-Location
$testsDir = Join-Path $aifxDir "tests"

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "URUCHAMIAM WSZYSTKIE TESTY - Support Breakout Strategy" -ForegroundColor Cyan
Write-Host "Working directory: $aifxDir" -ForegroundColor Gray
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

$totalTests = 0
$passedTests = 0
$failedTests = 0

function Run-Test {
    param($TestFile, $TestName)
    
    Write-Host "--------------------------------------------------------------------------------" -ForegroundColor Yellow
    Write-Host "TEST: $TestName" -ForegroundColor Yellow
    Write-Host "--------------------------------------------------------------------------------" -ForegroundColor Yellow
    
    $testPath = Join-Path $testsDir $TestFile
    $result = python $testPath 2>&1
    $exitCode = $LASTEXITCODE
    
    if ($exitCode -eq 0) {
        Write-Host "PASSED" -ForegroundColor Green
        $script:passedTests++
    } else {
        Write-Host "FAILED" -ForegroundColor Red
        Write-Host $result
        $script:failedTests++
    }
    
    Write-Host ""
    $script:totalTests++
}

function Run-Pytest {
    param($TestFile, $TestName)
    
    Write-Host "--------------------------------------------------------------------------------" -ForegroundColor Yellow
    Write-Host "TEST: $TestName" -ForegroundColor Yellow
    Write-Host "--------------------------------------------------------------------------------" -ForegroundColor Yellow
    
    $testPath = Join-Path $testsDir $TestFile
    $result = python -m pytest $testPath -v --tb=short 2>&1
    $exitCode = $LASTEXITCODE
    
    if ($exitCode -eq 0) {
        Write-Host "PASSED" -ForegroundColor Green
        $script:passedTests++
    } else {
        Write-Host "FAILED (some tests may have failed)" -ForegroundColor Red
        Write-Host $result
        $script:failedTests++
    }
    
    Write-Host ""
    $script:totalTests++
}

# Lista testow do uruchomienia
Run-Pytest "test_strategy.py" "Strategy Suite - pytest (35 test cases)"
Run-Test "test_close_at_eod.py" "Close At EOD (5 testow)"
Run-Test "test_min_slope.py" "Min Slope (2 testy)"
Run-Test "test_min_slope_integration.py" "Min Slope Integration (1 test)"
Run-Test "test_support_strategy.py" "Support Strategy (6 testow)"
Run-Test "test_short_positions.py" "Short Positions (5 testow)"
Run-Test "test_legend.py" "Legend (2 testy)"
Run-Test "test_hierarchical.py" "Hierarchical Lines (1 test)"
Run-Test "test_ascending_descending.py" "Ascending/Descending (3 testy)"

# Podsumowanie
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "PODSUMOWANIE" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "Calkowita liczba modulow testowych: $totalTests" -ForegroundColor White
Write-Host "Przeszly: $passedTests" -ForegroundColor Green
Write-Host "Nie przeszly: $failedTests" -ForegroundColor Red
Write-Host "================================================================================" -ForegroundColor Cyan

if ($failedTests -eq 0) {
    Write-Host "WSZYSTKIE TESTY PRZESZLY!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "NIEKTORE TESTY NIE PRZESZLY" -ForegroundColor Red
    exit 1
}
