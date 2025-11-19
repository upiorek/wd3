# PowerShell script to generate golden reference output
# Uruchamia backtest z wszystkimi opcjami i zapisuje wyniki jako wzorzec

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "GENEROWANIE GOLDEN REFERENCE - Support Breakout Strategy" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

# Parametry
$goldenDir = "golden"
$startDate = "2025-01-01"
$endDate = "2025-01-10"

# Utwórz folder golden
if (Test-Path $goldenDir) {
    Write-Host "Usuwam stary folder golden..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force $goldenDir
}
New-Item -ItemType Directory -Path $goldenDir | Out-Null
Write-Host "Utworzono folder: $goldenDir" -ForegroundColor Green
Write-Host ""

# Stwórz config dla golden test
$configPath = Join-Path $goldenDir "config_golden.json"

# Użyj Pythona do zapisania JSON (uniknie problemy z BOM/encoding)
$pythonCode = @"
import json
config = {
    'start_date': '$startDate',
    'end_date': '$endDate',
    'lookback_days': 3,
    'risk_pips': 50,
    'reward_ratio': 3,
    'retest_mode': False,
    'initial_capital': 10000,
    'risk_per_trade_pct': 2.0,
    'min_slope': 0.4,
    'show_volume': False,
    'mark_high_low': True,
    'generate_charts': True,
    'hierarchical_levels_below': 4,
    'hierarchical_levels_above': 4,
    'hierarchical_tolerance': 30,
    'allow_descending': True,
    'show_legend': True,
    'chart_dpi': 200,
    'close_at_eod': True
}
with open('$($configPath -replace '\\', '\\\\')', 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)
"@

python -c $pythonCode
Write-Host "Utworzono config: $configPath" -ForegroundColor Green
Write-Host ""

# Uruchom backtest i zapisz output
Write-Host "Uruchamiam backtest..." -ForegroundColor Cyan
Write-Host "Okres: $startDate do $endDate" -ForegroundColor Gray
Write-Host ""

$logPath = Join-Path $goldenDir "backtest_output.log"
$errorLogPath = Join-Path $goldenDir "backtest_errors.log"

# Ustaw UTF-8 encoding dla Pythona
$env:PYTHONIOENCODING = "utf-8"

# Przekieruj output do pliku
$process = Start-Process -FilePath "python" `
    -ArgumentList "run_support_backtest.py", $configPath `
    -NoNewWindow `
    -Wait `
    -PassThru `
    -RedirectStandardOutput $logPath `
    -RedirectStandardError $errorLogPath

$exitCode = $process.ExitCode

if ($exitCode -ne 0) {
    Write-Host "BLAD: Backtest zakonczyl sie bledem (exit code: $exitCode)" -ForegroundColor Red
    Write-Host "Sprawdz: $errorLogPath" -ForegroundColor Red
    exit 1
}

Write-Host "Backtest zakonczony pomyslnie" -ForegroundColor Green
Write-Host ""

# Przenieś wykresy do golden
$chartsDir = "support_charts"
if (Test-Path $chartsDir) {
    $goldenChartsDir = Join-Path $goldenDir "charts"
    Write-Host "Kopiuje wykresy..." -ForegroundColor Cyan
    Copy-Item -Recurse -Path $chartsDir -Destination $goldenChartsDir
    Write-Host "Skopiowano $(Get-ChildItem -Path $goldenChartsDir -Filter *.png | Measure-Object | Select-Object -ExpandProperty Count) wykresow" -ForegroundColor Green
}

# Skopiuj CSV z wynikami jeśli istnieje
$csvFile = "support_charts/support_breakout_results_*.csv"
$csvFiles = Get-ChildItem -Path "support_charts" -Filter "support_breakout_results_*.csv" -ErrorAction SilentlyContinue
if ($csvFiles) {
    foreach ($csv in $csvFiles) {
        Copy-Item -Path $csv.FullName -Destination $goldenDir
        Write-Host "Skopiowano: $($csv.Name)" -ForegroundColor Green
    }
}

Write-Host ""

# Podsumowanie
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "GOLDEN REFERENCE WYGENEROWANY" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "Lokalizacja: $goldenDir" -ForegroundColor White
Write-Host ""
Write-Host "Zawartość:" -ForegroundColor White
Write-Host "  - config_golden.json (konfiguracja)" -ForegroundColor Gray
Write-Host "  - backtest_output.log (logi backtestу)" -ForegroundColor Gray
Write-Host "  - backtest_errors.log (błędy jeśli wystąpiły)" -ForegroundColor Gray
Write-Host "  - charts/ (wykresy PNG)" -ForegroundColor Gray
Write-Host "  - *.csv (wyniki w CSV)" -ForegroundColor Gray
Write-Host ""
Write-Host "Możesz teraz zrobić refactoring i uruchomić:" -ForegroundColor Yellow
Write-Host "  .\tests\test_golden.ps1" -ForegroundColor Cyan
Write-Host ""
Write-Host "Test porówna wyniki przed i po refactoringu" -ForegroundColor Gray
Write-Host "================================================================================" -ForegroundColor Cyan
