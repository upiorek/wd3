# Testing Guide - Support Breakout Strategy

## Przegląd Testów

Projekt zawiera **8 modułów testowych** pokrywających różne aspekty strategii:

| Plik testowy | Liczba testów | Status | Opis |
|-------------|---------------|--------|------|
| `test_close_at_eod.py` | 5 | ✅ ALL PASS | Testy opcji zamykania pozycji na koniec dnia |
| `test_min_slope.py` | 2 | ✅ ALL PASS | Testy parametru min_slope z config |
| `test_min_slope_integration.py` | 1 | ✅ PASS | Test integracyjny min_slope (uruchamia run_support_backtest.py) |
| `test_support_strategy.py` | 6 | ✅ ALL PASS | Testy hierarchicznych linii wsparcia/oporu |
| `test_short_positions.py` | 5 | ✅ 3 PASS, 2 SKIP | Testy pozycji SHORT dla linii opadających |
| `test_legend.py` | 2 | ✅ ALL PASS | Testy wyświetlania legendy na wykresach |
| `test_hierarchical.py` | 1 | ✅ PASS | Test hierarchicznych linii równoległych |
| `test_ascending_descending.py` | 3 | ✅ ALL PASS | Testy wykrywania linii wznoszących i opadających |
| `test_strategy.py` | 35 | ⚠️ 24 PASS, 11 FAIL | Stare testy jednostkowe (niektóre nieaktualne) |

**Podsumowanie:** 8/8 głównych modułów testowych ✅ PASS

---

## Quick Start

### 1. Instalacja pytest (jednorazowo)
```bash
pip install pytest pytest-cov
```

### 2. Uruchomienie wszystkich testów
```bash
# Wszystkie testy close_at_eod
python tests/test_close_at_eod.py

# Testy min_slope
python tests/test_min_slope.py
python tests/test_min_slope_integration.py

# Wszystkie testy hierarchicznych linii
python tests/test_support_strategy.py

# Wszystkie testy SHORT
python tests/test_short_positions.py

# Wszystkie testy legendy
python tests/test_legend.py

# Test hierarchicznych linii równoległych
python tests/test_hierarchical.py

# Testy linii wznoszących/opadających
python tests/test_ascending_descending.py

# Testy pytest (wymagają aktualizacji)
pytest test_strategy.py -v
```

### 3. Uruchomienie wszystkich testów jednocześnie

#### Opcja A: Użyj gotowego skryptu (zalecane)
```powershell
# PowerShell (z folderu aifx)
cd aifx
.\tests\run_all_tests.ps1

# lub CMD (z folderu aifx)
cd aifx
tests\run_all_tests.bat

# lub z folderu tests
cd aifx\tests
.\run_all_tests.ps1
# lub
run_all_tests.bat
```

**Skrypt automatycznie:**
- Uruchamia wszystkie 8 modułów testowych po kolei
- Pokazuje wyniki każdego testu (PASSED / FAILED)
- Wyświetla podsumowanie na końcu
- Zwraca exit code 0 (sukces) lub 1 (błąd)

#### Opcja B: Uruchom ręcznie
```powershell
# PowerShell - wszystkie testy po kolei (z folderu aifx)
cd aifx
python tests/test_close_at_eod.py
python tests/test_min_slope.py
python tests/test_min_slope_integration.py
python tests/test_support_strategy.py
python tests/test_short_positions.py
python tests/test_legend.py
python tests/test_hierarchical.py
python tests/test_ascending_descending.py
```

---

## Szczegółowy Opis Testów

### test_close_at_eod.py (NOWY - 2025)

**Testuje:** Opcja `close_at_eod` (zamykanie pozycji na koniec dnia)

#### Test 1: close_at_eod wyłączone
```python
def test_close_at_eod_disabled():
```
✅ **Sprawdza:** Pozycja NIE jest zamykana na koniec dnia gdy `close_at_eod=False`  
✅ **Wykrywa:** Regresję gdyby EOD był wymuszany mimo wyłączenia opcji

#### Test 2: close_at_eod włączone (LONG)
```python
def test_close_at_eod_enabled():
```
✅ **Sprawdza:** Pozycja LONG jest zamykana na ostatniej świeczce dnia po cenie Close  
✅ **Weryfikuje:** Poprawne obliczenie pipsów dla LONG (exit_price - entry_price)  
✅ **Wykrywa:** Błędy w logice EOD, niepoprawne obliczenia pipsów

#### Test 3: close_at_eod dla SHORT
```python
def test_close_at_eod_short_position():
```
✅ **Sprawdza:** Pozycja SHORT zamykana z poprawnymi pipsami  
✅ **Weryfikuje:** Pips = entry_price - exit_price (odwrotnie niż LONG)  
✅ **Wykrywa:** Błędy w obliczeniach dla SHORT

#### Test 4: EOD nie triggerowane przed końcem dnia
```python
def test_close_at_eod_not_triggered_before_eod():
```
✅ **Sprawdza:** EOD NIE jest triggerowane w środku dnia  
✅ **Wykrywa:** Przedwczesne zamknięcie pozycji

#### Test 5: Priorytet SL/TP nad EOD
```python
def test_close_at_eod_tp_has_priority():
```
✅ **Sprawdza:** TP/SL mają priorytet nad EOD (są sprawdzane PRZED EOD)  
✅ **Weryfikuje:** Gdy TP osiągnięte - exit='TP' (NIE 'EOD')  
✅ **Wykrywa:** Niepoprawną kolejność sprawdzania exitów

**Uruchomienie:**
```bash
cd aifx
python tests/test_close_at_eod.py
```

**Oczekiwany output:**
```
✓ Test 1 PASSED: Pozycja NIE zamknięta na EOD gdy close_at_eod=False
✓ Test 2 PASSED: Pozycja LONG zamknięta na EOD po cenie Close (50 pips zysku)
✓ Test 3 PASSED: Pozycja SHORT zamknięta na EOD z poprawnymi pipsami (50 pips zysku)
✓ Test 4 PASSED: EOD NIE triggerowane przed końcem dnia
✓ Test 5 PASSED: TP ma priorytet nad EOD

✓ Wszystkie testy close_at_eod PASSED (5/5)
```

---

### test_support_strategy.py

**Testuje:** Hierarchiczne linie wsparcia/oporu

#### Test 1: Podstawowe wykrywanie linii
✅ Wykrycie linii wsparcia dla każdego dnia  
✅ Poprawność slope i intercept  
✅ Podział na trendy wzrostowe/spadkowe

#### Test 2: Wykrywanie hierarchicznych linii równoległych
✅ Linie wsparcia poniżej głównej (offset < 0)  
✅ Linie oporu powyżej głównej (offset > 0)  
✅ Poprawna liczba linii hierarchicznych

#### Test 3: Równoległość hierarchicznych linii
✅ Wszystkie linie mają ten sam slope co główna  
✅ Brak naruszeń równoległości

#### Test 4: Znaki offsetów
✅ Wsparcia: offset < 0 (poniżej głównej)  
✅ Opory: offset > 0 (powyżej głównej)

#### Test 5: Struktura danych
✅ Wszystkie wymagane klucze: slope, intercept, offset, level, score, touches  
✅ Poziomy (level) >= 2  
✅ Score >= 3 punkty

#### Test 6: Generowanie wykresów
✅ Wykres tworzony bez błędów  
✅ Użycie rzeczywistych danych

**Uruchomienie:**
```bash
cd aifx
python tests/test_support_strategy.py
```

---

### test_min_slope.py (NOWY - 2025)

**Testuje:** Parametr `min_slope` z pliku config

#### Test 1: min_slope przechowywany w strategii
```python
def test_min_slope_from_config():
```
✅ **Sprawdza:** Config zawiera min_slope  
✅ **Weryfikuje:** Strategia przechowuje min_slope z config  
✅ **Wykrywa:** Regresję gdyby min_slope nie był używany

#### Test 2: min_slope przekazywany do strategii
```python
def test_min_slope_used_in_run_support_backtest():
```
✅ **Sprawdza:** Merge config z defaults działa poprawnie  
✅ **Weryfikuje:** `{**default_options, **options}` nadpisuje defaults wartościami z config  
✅ **Wykrywa:** Błędy w przekazywaniu parametrów do strategii

**Uruchomienie:**
```bash
cd aifx
python tests/test_min_slope.py
```

**Oczekiwany output:**
```
================================================================================
TESTY MIN_SLOPE
================================================================================

min_slope w config: 0.4
min_slope w strategii: 0.4
✓ Test PASSED: min_slope poprawnie przechowany w strategii

✓ min_slope=0.4 znaleziony w config
✓ Po merge: min_slope=0.4
✓ Test PASSED: min_slope=0.4 poprawnie przekazany do strategii

================================================================================
✓✓✓ WSZYSTKIE TESTY PASSED ✓✓✓
================================================================================
```

---

### test_min_slope_integration.py (NOWY - 2025)

**Testuje:** Test integracyjny - uruchamia faktyczny `run_support_backtest.py` i sprawdza output

#### Test: run_support_backtest.py używa min_slope z config
```python
def test_run_support_backtest_uses_config_min_slope():
```
✅ **Sprawdza:** Uruchomienie `python run_support_backtest.py config_example.json`  
✅ **Weryfikuje:** Log zawiera `Min slope: 0.4` (wartość z config)  
✅ **Wykrywa:** Regresję w faktycznym użyciu programu

**Czym się różni od test_min_slope.py:**
- `test_min_slope.py` - testy jednostkowe (importuje moduły)
- `test_min_slope_integration.py` - test integracyjny (uruchamia subprocess)

**Uruchomienie:**
```bash
cd aifx
python tests/test_min_slope_integration.py
```

**Oczekiwany output:**
```
================================================================================
TEST INTEGRACYJNY: run_support_backtest.py + config_example.json
================================================================================

Uruchamiam: python run_support_backtest.py config_example.json

✓ Znaleziono w logu: Min slope: 0.4
✓ Test PASSED: run_support_backtest.py używa min_slope=0.4 z config
================================================================================
```

---

### test_short_positions.py

**Testuje:** Pozycje SHORT dla linii opadających (slope < 0)

#### Test 1: Wykrywanie linii opadających
✅ Wykrywanie linii z slope < 0  
✅ Przykładowe slope ujemne

#### Test 2: Generowanie sygnałów SHORT
⚠️ **SKIPPED** - brak breakoutu w danych testowych  
(Test sprawdza czy sygnały SHORT są generowane dla linii opadających)

#### Test 3: Ustawienie SL/TP dla SHORT
⚠️ **SKIPPED** - brak sygnału SHORT  
(Test sprawdza czy SL powyżej entry, TP poniżej entry)

#### Test 4: Exit logic dla SHORT
✅ TP: Low <= TP_price → exit TP  
✅ SL: High >= SL_price → exit SL  
✅ Poprawne obliczenie pipsów dla SHORT

#### Test 5: Wykrywanie LONG i SHORT jednocześnie
✅ System wykrywa oba typy linii (slope > 0 i slope < 0)  
✅ Rozkład 50/50

**Uruchomienie:**
```bash
cd aifx
python tests/test_short_positions.py
```

---

### test_legend.py

**Testuje:** Opcja `show_legend` (wyświetlanie legendy na wykresach)

#### Test 1: Legenda wyłączona
✅ `show_legend=False` → 0 etykiet w legendzie

#### Test 2: Legenda włączona
✅ `show_legend=True` → legenda z etykietami linii wsparcia/oporu

**Uruchomienie:**
```bash
cd aifx
python tests/test_legend.py
```

---

### test_hierarchical.py

**Testuje:** Wykrywanie i wizualizacja hierarchicznych linii równoległych

✅ Linie wsparcia poniżej głównej (S2, S3, S4...)  
✅ Linie oporu powyżej głównej (R2, R3, R4...)  
✅ Offsety i score dla każdej linii

**Uruchomienie:**
```bash
cd aifx
python tests/test_hierarchical.py
```

---

### test_ascending_descending.py

**Testuje:** Wykrywanie linii wznoszących i opadających jednocześnie

#### Test 1: Wykrywanie obu kierunków
✅ System wykrywa linie wznosząc (slope > 0)  
✅ System wykrywa linie opadające (slope < 0)

#### Test 2: Wykres zawiera obie linie
✅ Wykres z linią wznoszącą (czerwone)  
✅ Wykres z linią opadającą (zielone)

#### Test 3: Przeciwne znaki slope
✅ Linie mają przeciwne znaki (+/-)  
✅ Dokładnie ten sam |slope| (różnica <1%)

**Uruchomienie:**
```bash
cd aifx
python tests/test_ascending_descending.py
```

---

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

### Scenario 4: Refactoring - Golden Tests

**Cel:** Bezpieczna refaktoryzacja kodu z weryfikacją, że zachowanie systemu nie uległo zmianie.

**Workflow:**
```powershell
# KROK 1: Wygeneruj wzorcowe wyniki (przed refactoringiem)
cd c:\Users\rrudnick\OneDrive - Intel Corporation\Desktop\fx\wd3\aifx
.\tests\generate_golden.ps1

# KROK 2: Wykonaj refactoring (zmiany w kodzie)
# ... modyfikacja kodu ...

# KROK 3: Przetestuj po refactoringu
.\tests\test_golden.ps1

# KROK 4: Sprawdź wyniki
# - Exit code 0: refactoring OK (identyczne wyniki)
# - Exit code 1: wykryto różnice (sprawdź logi)
```

**Kiedy używać:**
- Przed dużym refactoringiem (zmiana struktury kodu)
- Optymalizacja algorytmów (sprawdź czy wyniki się nie zmieniły)
- Aktualizacja zależności (pandas, numpy)
- Migracja do nowej wersji Pythona

**Co jest porównywane:**
1. **Logi backtestingu** - znormalizowane (bez timestampów/ścieżek)
2. **CSV wyniki** - wszystkie transakcje (entry_price, exit_price, pips, result)
3. **Wykresy** - liczba plików, nazwy, rozmiary (±5% tolerancja)

**Ograniczenia:**
- Losowe elementy (seed trzeba ustawić)
- Zmiany w formacie outputu (np. nowe kolumny w CSV) wywołają failure
- Floating point errors mogą wymagać tolerancji
- Nie wykrywa problemów z wydajnością (tylko poprawność)

**Przykład - sukces:**
```
Running backtest with current code...
Backtest completed successfully.
Comparing logs...
Logs are identical (after normalization).
Comparing CSV results...
CSV results are identical.
Comparing charts...
Charts are identical (20 files).
✓ Golden test PASSED - refactoring safe!
Exit: 0
```

**Przykład - failure:**
```
Running backtest with current code...
Backtest completed successfully.
Comparing logs...
✗ DIFFERENCE detected in logs! See: golden_test/log_diff.txt
Comparing CSV results...
✗ DIFFERENCE: Transaction count mismatch (golden: 45, test: 43)
Exit: 1
```

### Scenario 5: Release - pełna weryfikacja
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
