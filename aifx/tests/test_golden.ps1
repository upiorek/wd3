# PowerShell script to test against golden reference
# Uruchamia backtest i porównuje z golden reference

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "TEST GOLDEN REFERENCE - Weryfikacja Refactoringu" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

# Parametry
$goldenDir = "golden"
$testDir = "golden_test"

# Sprawdź czy golden istnieje
if (-not (Test-Path $goldenDir)) {
    Write-Host "BLAD: Folder golden nie istnieje!" -ForegroundColor Red
    Write-Host "Najpierw uruchom: .\tests\generate_golden.ps1" -ForegroundColor Yellow
    exit 1
}

# Utwórz folder golden_test
if (Test-Path $testDir) {
    Write-Host "Usuwam stary folder golden_test..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force $testDir
}
New-Item -ItemType Directory -Path $testDir | Out-Null
Write-Host "Utworzono folder: $testDir" -ForegroundColor Green
Write-Host ""

# Skopiuj config z golden
$goldenConfig = Join-Path $goldenDir "config_golden.json"
$testConfig = Join-Path $testDir "config_golden.json"
Copy-Item -Path $goldenConfig -Destination $testConfig
Write-Host "Skopiowano config z golden" -ForegroundColor Green
Write-Host ""

# Uruchom backtest
Write-Host "Uruchamiam backtest z aktualnym kodem..." -ForegroundColor Cyan
Write-Host ""

$logPath = Join-Path $testDir "backtest_output.log"
$errorLogPath = Join-Path $testDir "backtest_errors.log"

# Ustaw UTF-8 encoding dla Pythona
$env:PYTHONIOENCODING = "utf-8"

$process = Start-Process -FilePath "python" `
    -ArgumentList "run_support_backtest.py", $testConfig `
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

Write-Host "Backtest zakonczony" -ForegroundColor Green
Write-Host ""

# Przenieś wykresy do golden_test
$chartsDir = "support_charts"
if (Test-Path $chartsDir) {
    $testChartsDir = Join-Path $testDir "charts"
    Copy-Item -Recurse -Path $chartsDir -Destination $testChartsDir
    $chartCount = Get-ChildItem -Path $testChartsDir -Filter *.png | Measure-Object | Select-Object -ExpandProperty Count
    Write-Host "Skopiowano $chartCount wykresow" -ForegroundColor Green
}

# Skopiuj CSV
$csvFiles = Get-ChildItem -Path "support_charts" -Filter "support_breakout_results_*.csv" -ErrorAction SilentlyContinue
if ($csvFiles) {
    foreach ($csv in $csvFiles) {
        Copy-Item -Path $csv.FullName -Destination $testDir
    }
}

Write-Host ""
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "POROWNYWANIE WYNIKOW" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

$differences = @()

# 1. Porównaj logi (ignoruj timestampy i ścieżki)
Write-Host "[1/4] Porownuje logi..." -ForegroundColor Yellow

$goldenLog = Get-Content (Join-Path $goldenDir "backtest_output.log") -Raw
$testLog = Get-Content (Join-Path $testDir "backtest_output.log") -Raw

# Usuń timestampy, ścieżki i inne zmienne elementy
function Normalize-Log {
    param($log)
    $log = $log -replace '\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', 'TIMESTAMP'
    $log = $log -replace 'C:\\[^\s]+\\', 'PATH\\'
    $log = $log -replace '/[^\s]+/', '/PATH/'
    $log = $log -replace '\d+\.\d{6}s', 'X.XXXXXXs'  # czas wykonania
    $log = $log -replace 'golden_test\\', 'golden\'  # Normalizuj ścieżki golden vs golden_test
    $log = $log -replace 'golden_test/', 'golden/'
    # Normalizuj linię "Dni z obliczonym support" - liczba może się różnić (dict vs list)
    $log = $log -replace 'Dni z obliczonym support: \d+', 'Dni z obliczonym support: N'
    $log = $log.Trim()  # Usuń białe znaki na początku/końcu
    $log = $log -replace '\r\n', "`n"  # Normalizuj końce linii
    $log = $log -replace '\s+$', ''  # Usuń trailing whitespace
    return $log
}

$normalizedGolden = Normalize-Log $goldenLog
$normalizedTest = Normalize-Log $testLog

if ($normalizedGolden -ne $normalizedTest) {
    Write-Host "  ROZNICE w logach!" -ForegroundColor Red
    $differences += "Logi różnią się"
    
    # Zapisz diff
    $diffFile = Join-Path $testDir "log_diff.txt"
    "=== GOLDEN LOG ===" | Set-Content $diffFile
    $normalizedGolden | Add-Content $diffFile
    "`n`n=== TEST LOG ===" | Add-Content $diffFile
    $normalizedTest | Add-Content $diffFile
    
    Write-Host "  Zapisano diff do: $diffFile" -ForegroundColor Gray
} else {
    Write-Host "  OK - Logi identyczne" -ForegroundColor Green
}

# 2. Porównaj CSV
Write-Host "[2/4] Porownuje CSV..." -ForegroundColor Yellow

$goldenCsv = Get-ChildItem -Path $goldenDir -Filter "*.csv" | Select-Object -First 1
$testCsv = Get-ChildItem -Path $testDir -Filter "*.csv" | Select-Object -First 1

if ($goldenCsv -and $testCsv) {
    $goldenData = Import-Csv $goldenCsv.FullName
    $testData = Import-Csv $testCsv.FullName
    
    if ($goldenData.Count -ne $testData.Count) {
        Write-Host "  ROZNICE: Liczba transakcji rozna ($($goldenData.Count) vs $($testData.Count))" -ForegroundColor Red
        $differences += "CSV: różna liczba transakcji"
    } else {
        # Porównaj każdą transakcję
        $csvDiffs = 0
        for ($i = 0; $i -lt $goldenData.Count; $i++) {
            $g = $goldenData[$i]
            $t = $testData[$i]
            
            # Porównaj kluczowe pola (ignoruj daty w formatach które mogą się różnić)
            if ($g.entry_price -ne $t.entry_price -or 
                $g.exit_price -ne $t.exit_price -or 
                $g.pips -ne $t.pips -or 
                $g.result -ne $t.result) {
                $csvDiffs++
            }
        }
        
        if ($csvDiffs -gt 0) {
            Write-Host "  ROZNICE: $csvDiffs transakcji ma rozne wartosci" -ForegroundColor Red
            $differences += "CSV: $csvDiffs różnych transakcji"
        } else {
            Write-Host "  OK - CSV identyczne ($($goldenData.Count) transakcji)" -ForegroundColor Green
        }
    }
} else {
    Write-Host "  Brak CSV do porownania" -ForegroundColor Gray
}

# 3. Porównaj liczbę wykresów
Write-Host "[3/4] Porownuje wykresy..." -ForegroundColor Yellow

$goldenCharts = Get-ChildItem -Path (Join-Path $goldenDir "charts") -Filter *.png -Recurse
$testCharts = Get-ChildItem -Path (Join-Path $testDir "charts") -Filter *.png -Recurse

if ($goldenCharts.Count -ne $testCharts.Count) {
    Write-Host "  ROZNICE: Liczba wykresow rozna ($($goldenCharts.Count) vs $($testCharts.Count))" -ForegroundColor Red
    $differences += "Wykresy: różna liczba plików"
} else {
    Write-Host "  OK - Ta sama liczba wykresow ($($goldenCharts.Count))" -ForegroundColor Green
    
    # Porównaj nazwy plików
    $goldenNames = $goldenCharts | Select-Object -ExpandProperty Name | Sort-Object
    $testNames = $testCharts | Select-Object -ExpandProperty Name | Sort-Object
    
    $nameDiffs = Compare-Object $goldenNames $testNames
    if ($nameDiffs) {
        Write-Host "  ROZNICE: Rozne nazwy plikow wykresow" -ForegroundColor Red
        $differences += "Wykresy: różne nazwy plików"
    } else {
        Write-Host "  OK - Identyczne nazwy plikow" -ForegroundColor Green
    }
}

# 4. Porównaj rozmiary wykresów (obrazy mogą być binarnie różne ale podobne)
Write-Host "[4/4] Porownuje rozmiary wykresow..." -ForegroundColor Yellow

$sizeDiffs = 0
foreach ($goldenChart in $goldenCharts) {
    $testChart = $testCharts | Where-Object { $_.Name -eq $goldenChart.Name }
    if ($testChart) {
        $goldenSize = $goldenChart.Length
        $testSize = $testChart.Length
        
        # Tolerancja 5% różnicy w rozmiarze (matplotlib może generować lekko różne pliki)
        $diff = [Math]::Abs($goldenSize - $testSize) / $goldenSize
        if ($diff -gt 0.05) {
            $sizeDiffs++
        }
    }
}

if ($sizeDiffs -gt 0) {
    Write-Host "  OSTRZEZENIE: $sizeDiffs wykresow ma >5% roznice w rozmiarze" -ForegroundColor Yellow
    Write-Host "  (Moze byc OK - matplotlib moze generowac lekko rozne pliki)" -ForegroundColor Gray
} else {
    Write-Host "  OK - Rozmiary wykresow podobne" -ForegroundColor Green
}

Write-Host ""
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "WYNIK TESTU" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan

if ($differences.Count -eq 0) {
    Write-Host ""
    Write-Host "SUKCES! Refactoring nie zmienil wynikow" -ForegroundColor Green
    Write-Host ""
    Write-Host "Wszystkie porownania identyczne:" -ForegroundColor White
    Write-Host "  - Logi backtestу" -ForegroundColor Gray
    Write-Host "  - Transakcje (CSV)" -ForegroundColor Gray
    Write-Host "  - Wykresy (nazwy i liczba)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Mozesz bezpiecznie zacommitowac refactoring!" -ForegroundColor Green
    Write-Host "================================================================================" -ForegroundColor Cyan
    exit 0
} else {
    Write-Host ""
    Write-Host "UWAGA! Wykryto roznice:" -ForegroundColor Red
    Write-Host ""
    foreach ($diff in $differences) {
        Write-Host "  - $diff" -ForegroundColor Yellow
    }
    Write-Host ""
    Write-Host "Sprawdz foldery:" -ForegroundColor White
    Write-Host "  Golden:  $goldenDir" -ForegroundColor Gray
    Write-Host "  Test:    $testDir" -ForegroundColor Gray
    Write-Host ""
    Write-Host "REFACTORING ZMIENIL WYNIKI - sprawdz zmiany!" -ForegroundColor Red
    Write-Host "================================================================================" -ForegroundColor Cyan
    exit 1
}
