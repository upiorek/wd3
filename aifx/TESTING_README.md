# Uruchamianie Testów - AIFX

**UWAGA: Wszystkie testy znajdują się w katalogu `tests/`**

## Metoda 1: Uruchom wszystkie testy (Zalecane)

### Windows (PowerShell/CMD):
```bash
cd tests
python run_all_tests.py
```

Lub:
```bash
cd tests
run_all_tests.bat
```

### Linux/Mac:
```bash
cd tests
chmod +x run_all_tests.sh
./run_all_tests.sh
```

Lub:
```bash
cd tests
python run_all_tests.py
```

## Metoda 2: Uruchom pojedyncze testy

### Test strategii support breakout (wszystkie 35 testów):
```bash
cd tests
python test_strategy.py
```

### Test hierarchicznych linii (6 testów):
```bash
cd tests
python test_support_strategy.py
```

### Test impulse detector:
```bash
python impulse_detector.py --test
```

## Tryb Verbose

Aby zobaczyć pełny output wszystkich testów:
```bash
cd tests
python run_all_tests.py --verbose
```

## Wymagania

- Python 3.8+
- pandas, numpy, matplotlib, mplfinance, scipy
- pytest (dla test_strategy.py)

## Struktura Testów

**Lokalizacja: Katalog `tests/`**

1. **test_strategy.py** (35 testów, pytest)
   - Inicjalizacja strategii
   - Obliczanie wskaźników
   - Wykrywanie impulsów
   - Linie wsparcia
   - Warunki wejścia/wyjścia
   - Backtest engine
   - Plotting
   - Integracja danych
   - Regresje
   - Performance
   - Edge cases

2. **test_support_strategy.py** (6 testów, custom)
   - Podstawowe wykrywanie linii wsparcia
   - Wykrywanie hierarchicznych linii równoległych
   - Równoległość linii (identyczny slope)
   - Znaki offsetów (wsparcia < 0, opory > 0)
   - Struktura danych
   - Generowanie wykresów

3. **impulse_detector.py --test** (1 test, katalog główny)
   - Test hierarchicznych linii na syntetycznych danych
   - **Uwaga**: impulse_detector.py znajduje się w katalogu głównym (aifx/), nie w tests/

## Output

### Sukces:
```
################################################################################
# ✅✅✅ WSZYSTKIE TESTY PASSED (2/2) ✅✅✅
################################################################################
```

### Failure:
```
################################################################################
# ❌ 1/2 TESTÓW FAILED
################################################################################
```

## Troubleshooting

### Problem z kodowaniem (UnicodeEncodeError):
Użyj `run_all_tests.py` lub `run_all_tests.bat` które ustawiają UTF-8.

### Brak modułu pytest:
```bash
pip install pytest
```

### Brak pliku FUS100.15.csv:
Test `test_support_strategy.py` (TEST 6) wymaga pliku FUS100.15.csv. 
Jeśli plik nie istnieje, test użyje syntetycznych danych.

## Continuous Integration

Dla CI/CD pipelines:
```bash
cd tests
python run_all_tests.py
exit $?
```

## Szybkie Sprawdzenie

Jeśli chcesz tylko sprawdzić czy wszystko działa:
```bash
cd tests
python run_all_tests.py
```

Exit code 0 = wszystkie testy OK, exit code 1 = są błędy.

## Struktura Katalogów

```
aifx/
├── impulse_detector.py         # Główny moduł (z inline testem)
├── support_breakout_strategy.py
├── TESTING_README.md           # Ta dokumentacja
└── tests/                      # Wszystkie testy tutaj
    ├── test_strategy.py        # 35 testów pytest
    ├── test_support_strategy.py # 6 testów hierarchicznych linii
    ├── run_all_tests.py        # Skrypt uruchamiający (Python)
    ├── run_all_tests.bat       # Skrypt uruchamiający (Windows)
    └── run_all_tests.sh        # Skrypt uruchamiający (Linux/Mac)
```
