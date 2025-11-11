# Quick Reference - Testowanie Automatyczne

## ⚡ Najważniejsze Komendy

```bash
# Szybki test podczas developmentu (5s)
pytest test_strategy.py -v -m "not slow"

# Pełna walidacja (6s)
pytest test_strategy.py -v

# Pokrycie kodu
pytest test_strategy.py --cov=support_breakout_strategy --cov-report=html
```

## 🎯 Czego Szukać

### ✅ PASSED - wszystko OK
```
test_strategy.py::TestEntryConditions::test_breakout_detection_logic PASSED [48%]
```
→ Test przeszedł, funkcjonalność działa poprawnie

### ❌ FAILED - znaleziono błąd
```
FAILED test_strategy.py::TestEntryConditions::test_breakout_detection_logic
AssertionError: Nie wykryto breakout mimo spełnienia warunków
```
→ Kod ma błąd, trzeba naprawić przed commitem

## 📊 Wyniki Testów

**27/27 PASSED (100%)**  
**Pokrycie: 66%**  
**Czas: 6 sekund**

## 🐛 Znalezione Błędy

Testy automatycznie wykryły 6 błędów produkcyjnych:
1. Brak parametru min_slope
2. Zła domyślna risk_pips (20→50)
3. Zła domyślna reward_ratio (2.5→3)
4. Brak self.reward_ratio
5. Hardcoded 0.1 zamiast self.min_slope
6. Hardcoded label wykresu

## 🔄 Workflow

1. **Zmień kod** → Edytuj support_breakout_strategy.py
2. **Zapisz** → Ctrl+S
3. **Testuj** → `pytest test_strategy.py -v -m "not slow"`
4. **Sprawdź** → 5s później masz wynik
5. **Commit** → Jeśli PASSED, możesz commitować

## 📁 Pliki Testowe

- `test_strategy.py` - 27 testów automatycznych
- `pytest.ini` - konfiguracja pytest
- `TESTING_GUIDE.md` - szczegółowy przewodnik
- `TEST_RESULTS.md` - wyniki i statystyki

## 💡 Pro Tips

- Uruchamiaj testy po każdej zmianie (5s to nic)
- `-m "not slow"` pomija test wydajności (szybsze iteracje)
- `--tb=line` pokazuje tylko linię błędu (czytelniejsze)
- `--cov` generuje raport pokrycia (użyj przed release)

## 🎓 Korzyści

✅ Automatyczna detekcja błędów  
✅ Pewność przy zmianach  
✅ Dokumentacja API w testach  
✅ 5-6 sekund feedback loop  
✅ Zero manual testing  

---
**Ostatnia aktualizacja:** 2025-01-XX  
**Status:** ✅ Production Ready
