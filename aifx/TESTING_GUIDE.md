# Testing Guide - Support Breakout Strategy

## Quick Start

### 1. Instalacja pytest (jednorazowo)
```bash
pip install pytest pytest-cov
```

### 2. Uruchomienie wszystkich testów
```bash
# Podstawowe uruchomienie
pytest test_strategy.py -v

# Z pokryciem kodu (coverage)
pytest test_strategy.py --cov=support_breakout_strategy --cov-report=html

# Tylko szybkie testy (pomija testy wydajnościowe)
pytest test_strategy.py -v -m "not slow"
```

### 3. Uruchomienie konkretnej kategorii testów
```bash
# Tylko testy inicjalizacji
pytest test_strategy.py::TestStrategyInitialization -v

# Tylko testy wykrywania impulsów
pytest test_strategy.py::TestImpulseDetection -v

# Tylko testy backtest engine
pytest test_strategy.py::TestBacktestEngine -v
```

---

## Co Testują Poszczególne Klasy

### TestStrategyInitialization
✅ Poprawność domyślnych parametrów  
✅ Zachowanie custom parametrów  
✅ Inicjalizacja cache structures  

**Wykrywa:** Błędy w konstruktorze, złe defaulty

---

### TestIndicatorCalculation
✅ Obecność wszystkich wymaganych kolumn (Support_Slope, EMA_20, ATR_14, etc.)  
✅ Poprawność obliczeń EMA (w rozsądnym zakresie)  
✅ Poprawność obliczeń ATR (dodatni, rozsądny zakres)  
✅ Support_Price nie wszystkie NaN  

**Wykrywa:** Błędy w calculate_indicators, brakujące kolumny, błędne obliczenia

---

### TestImpulseDetection
✅ Wykrywanie oczywistych impulsów (volume spike + price move)  
✅ Zwracanie listy indeksów  
✅ Poprawność indeksów (w zakresie DataFrame)  

**Wykrywa:** Regresje w _detect_impulses_full, źle wykryte impulsy

---

### TestSupportLine
✅ Zwracanie tuple (slope, intercept)  
✅ Typy danych (float lub NaN)  
✅ Działanie min_slope filter  

**Wykrywa:** Błędy w _find_support_line, niepoprawny slope filter

---

### TestEntryConditions
✅ Wymaganie Support_Price dla wejścia  
✅ Wymaganie przynajmniej 1 poprzedniej świecy  
✅ Logika breakout (prev <= support < current)  

**Wykrywa:** Błędy w should_enter, fałszywe sygnały wejścia

---

### TestExitConditions
✅ Wykrywanie Stop Loss  
✅ Wykrywanie Take Profit  
✅ Brak wyjścia gdy cena w zakresie  

**Wykrywa:** Błędy w check_exit, niewłaściwe zamknięcie pozycji

---

### TestBacktestEngine
✅ Poprawna inicjalizacja  
✅ Zwracanie słownika wyników  
✅ Obecność wszystkich kluczy (trades, win_rate, total_pnl, etc.)  
✅ Zachowanie kapitału (final = initial + PnL)  
✅ Poprawność win_rate  

**Wykrywa:** Błędy w backtest_engine.py, niepoprawne statystyki

---

### TestDataIntegrity
✅ Wymaganie DateTime (index lub kolumna)  
✅ Wymagane kolumny (OHLCV)  

**Wykrywa:** Błędy obsługi brakujących danych

---

### TestRegressionPrevention
✅ **KRYTYCZNE:** DateTime offset consistency (po filtrowaniu)  
✅ Działanie daily cache mechanism  
✅ Skuteczność slope filter  

**Wykrywa:** Znane bugi które już naprawiliśmy (zapobiega powrotom)

---

### TestPerformance
⚡ Wydajność calculate_indicators (<5s dla tygodnia danych)  

**Wykrywa:** Regresje wydajnościowe, wolne pętle

---

## Interpretacja Wyników

### ✅ Wszystkie testy przeszły (PASS)
```
======================== 45 passed in 3.21s ========================
```
**Znaczenie:** Kod działa poprawnie, nie ma regresji

### ❌ Testy nie przeszły (FAIL)
```
FAILED test_strategy.py::TestEntryConditions::test_breakout_detection_logic
```
**Znaczenie:** Znaleziono bug w logice breakout  
**Akcja:** Sprawdź why test failed, napraw kod, uruchom ponownie

### ⚠️ Testy pominięte (SKIP)
```
======================== 40 passed, 5 skipped in 2.10s ========================
```
**Znaczenie:** Testy oznaczone jako @pytest.mark.slow zostały pominięte  
**Akcja:** OK, testy wydajnościowe można pomijać podczas development

---

## Continuous Integration (CI) - Automatyzacja

### GitHub Actions (opcjonalnie)
Stwórz plik `.github/workflows/tests.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: 3.11
      - run: pip install pytest pandas numpy scipy matplotlib mplfinance
      - run: pytest test_strategy.py -v
```

**Efekt:** Testy uruchamiają się automatycznie przy każdym commit/push

---

## Pre-commit Hook (Local)

Stwórz plik `.git/hooks/pre-commit`:
```bash
#!/bin/sh
echo "Uruchamianie testów przed commitem..."
pytest test_strategy.py -v -m "not slow"

if [ $? -ne 0 ]; then
    echo "❌ Testy nie przeszły - commit anulowany"
    exit 1
fi

echo "✅ Wszystkie testy przeszły"
```

**Efekt:** Niemożliwy commit jeśli testy nie przejdą

---

## Coverage Report

### Generowanie raportu pokrycia
```bash
pytest test_strategy.py --cov=support_breakout_strategy --cov=backtest_engine --cov-report=html
```

**Output:** Folder `htmlcov/` z interaktywnym raportem  
**Otwórz:** `htmlcov/index.html` w przeglądarce

**Interpretacja:**
- **>80% coverage** = dobry poziom testów
- **<50% coverage** = za mało testów, dużo nieprzetestowanego kodu

---

## Przykładowe Scenariusze

### Scenario 1: Modyfikujesz _detect_impulses_full
```bash
# Po edycji kodu
pytest test_strategy.py::TestImpulseDetection -v

# Jeśli PASS - OK
# Jeśli FAIL - regresja, sprawdź co zepsułeś
```

### Scenario 2: Dodajesz nowy parametr do strategii
```bash
# Dodaj test do TestStrategyInitialization
# Uruchom wszystkie testy inicjalizacji
pytest test_strategy.py::TestStrategyInitialization -v
```

### Scenario 3: Naprawiasz bug w backtest_engine
```bash
# Po naprawie
pytest test_strategy.py::TestBacktestEngine -v

# Jeśli wszystkie PASS - bug fixed
# Dodaj nowy test który wykrywa ten bug (regression test)
```

### Scenario 4: Release - pełna weryfikacja
```bash
# Uruchom WSZYSTKIE testy (włącznie z wydajnościowymi)
pytest test_strategy.py -v

# Wygeneruj coverage report
pytest test_strategy.py --cov=support_breakout_strategy --cov-report=html

# Sprawdź czy coverage >80%
# Sprawdź czy wszystkie testy PASS
```

---

## Dodawanie Własnych Testów

### Template dla nowego testu
```python
class TestMojaNowaFunkcja:
    """Opis co testujesz"""
    
    def test_podstawowe_dzialanie(self, strategy_default, sample_data):
        """Sprawdza czy funkcja działa w podstawowym przypadku"""
        # Arrange (przygotowanie danych)
        df = sample_data.copy()
        
        # Act (wywołanie funkcji)
        result = strategy_default.moja_funkcja(df)
        
        # Assert (sprawdzenie wyników)
        assert result is not None
        assert isinstance(result, expected_type)
        assert result == expected_value
    
    def test_edge_case_pusty_df(self, strategy_default):
        """Sprawdza zachowanie dla pustego DataFrame"""
        df = pd.DataFrame()
        
        # Powinien zwrócić None lub rzucić sensowny błąd
        result = strategy_default.moja_funkcja(df)
        assert result is None  # lub pytest.raises(ValueError)
```

---

## FAQ

**Q: Jak często uruchamiać testy?**  
A: Po każdej większej zmianie w kodzie (przed commitem)

**Q: Czy muszę pisać nowe testy?**  
A: Nie, ale jeśli dodajesz nową funkcję - warto dodać test

**Q: Co jeśli test failuje ale kod wydaje się OK?**  
A: Test może być źle napisany - sprawdź warunki assert, może trzeba je dostosować

**Q: Jak długo trwają testy?**  
A: Podstawowe testy: 2-5 sekund  
   Z testami wydajności: 10-15 sekund  
   Z coverage: 15-20 sekund

**Q: Czy testy wymagają danych z FUS100.15.csv?**  
A: NIE - testy używają syntetycznych danych (fixtures)

---

## Troubleshooting

### Problem: ModuleNotFoundError: No module named 'pytest'
**Rozwiązanie:**
```bash
pip install pytest
```

### Problem: ModuleNotFoundError: No module named 'support_breakout_strategy'
**Rozwiązanie:**
```bash
# Uruchom pytest z katalogu gdzie są pliki .py
cd c:\Users\rrudnick\OneDrive - Intel Corporation\Desktop\fx\aifx_2
pytest test_strategy.py -v
```

### Problem: Wszystkie testy PASS ale kod ma bug
**Rozwiązanie:** Dodaj nowy test który wykrywa ten bug (regression test)

### Problem: Testy trwają bardzo długo
**Rozwiązanie:**
```bash
# Pomiń testy wydajnościowe
pytest test_strategy.py -v -m "not slow"
```

---

## Podsumowanie

✅ **45 testów** pokrywających:
- Inicjalizację strategii
- Obliczanie wskaźników (EMA, ATR, Support)
- Wykrywanie impulsów (7 kryteriów)
- Wyznaczanie linii wsparcia
- Warunki wejścia/wyjścia
- Silnik backtestingu
- Integralność danych
- Zapobieganie regresji (znane bugi)
- Wydajność

✅ **Zero kodowania** - tylko uruchomienie `pytest test_strategy.py -v`

✅ **Automatic regression detection** - każda zmiana kodu jest weryfikowana

✅ **Fast feedback** - 2-5 sekund na pełny test suite

---

**Użycie:**
```bash
# Development: szybkie sprawdzenie po zmianach
pytest test_strategy.py -v -m "not slow"

# Pre-commit: weryfikacja przed commitem
pytest test_strategy.py -v

# Release: pełna weryfikacja + coverage
pytest test_strategy.py -v --cov=support_breakout_strategy --cov-report=html
```
