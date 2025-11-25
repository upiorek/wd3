# Support Breakout Strategy - Hierarchiczne Linie Równoległe

## Przegląd

Support Breakout Strategy to zaawansowany system tradingowy wykrywający breakouty wraz z **hierarchicznymi liniami równoległymi** (S2, S3, R2, R3).

Główne cechy:
- ✅ **Dwa tryby lookback**: days (dni handlowe) lub candles (liczba świeczek)
- ✅ Wykrywanie głównej linii wsparcia/oporu z poprzednich N dni/świeczek
- ✅ **Hierarchiczne linie równoległe** poniżej (S2, S3) i powyżej (R2, R3) głównej
- ✅ Pozycje **LONG** (linie wznosząc) i **SHORT** (linie opadające)
- ✅ Integracja z `impulse_detector` dla wykrywania impulsów
- ✅ Wizualizacja wszystkich linii z gradientowymi kolorami i opisami
- ✅ **Formaty danych**: Bossa (TSV) i mBank (CSV semicolon)
- ✅ **Auto-detection**: automatyczne wykrywanie zakresu dat z pliku

## Linie Wznosząc vs Opadające

System automatycznie wykrywa dwa typy linii:

### 🟢 Linie WZNOSZĄC (slope > 0) → Strategia LONG
- **S1**: główna linia wsparcia (czerwona, ciągła, grubość 4)
- **S2, S3, S4...**: linie wsparcia PONIŻEJ głównej (darkred, maroon, brown...)
- **R2, R3, R4...**: linie oporu POWYŻEJ głównej (blue, dodgerblue, deepskyblue...)
- **Breakout**: gdy Close > S1 (w górę)
- **SL**: poniżej entry, **TP**: powyżej entry

### 🔴 Linie OPADAJĄCE (slope < 0) → Strategia SHORT
- **R1**: główna linia oporu (zielona, ciągła, grubość 4)
- **S2, S3, S4...**: linie wsparcia PONIŻEJ głównej (darkred, maroon, brown...)
- **R2, R3, R4...**: linie oporu POWYŻEJ głównej (blue, dodgerblue, deepskyblue...)
- **Breakout**: gdy Close < R1 (w dół)
- **SL**: powyżej entry, **TP**: poniżej entry

### Konfiguracja

```json
{
  "data_file": "FUS100.15.csv",
  "data_format": "bossa",       // "bossa" (TSV) lub "mbank" (CSV semicolon)
  "start_date": "2025-10-01",   // lub "auto" dla pierwszej świeczki
  "end_date": "2025-10-10",     // lub "auto" dla ostatniej świeczki
  
  "lookback_mode": "days",      // "days" (dni handlowe) lub "candles" (liczba świeczek)
  "lookback_days": 3,           // Używane gdy lookback_mode="days"
  "lookback_candles": 96,       // Używane gdy lookback_mode="candles" (96 = ~1 dzień M15)
  
  "min_slope": 0.4,             // Minimalny |slope| (bezwzględna wartość)
  "allow_descending": true,     // Wykrywaj linie opadające (SHORT)
  "hierarchical_levels_below": 4,
  "hierarchical_levels_above": 4,
  "hierarchical_tolerance": 30
}
```

## Tryby Lookback

### 📅 Tryb "days" (domyślny)
- Wykrywa linie na podstawie **N pełnych dni handlowych**
- Przykład: `lookback_days=3` → ostatnie 3 dni
- Generuje **wykres dla każdego dnia** w okresie backtestingu
- Idealne dla strategii wielodniowych

### 🕯️ Tryb "candles"
- Wykrywa linie na podstawie **N ostatnich świeczek**
- Przykład: `lookback_candles=96` → ostatnie 96 świeczek (≈1 dzień dla M15)
- Generuje **tylko jeden wykres** dla ostatniej daty
- **Ważne**: wykres pokazuje świeczki użyte do wykrywania (PRZED datą, nie włącznie)
- Idealne dla backtestingu intraday i optymalizacji

### Konwersja candles → days (M15)
- 1 dzień handlowy ≈ 96 świeczek (24h × 4 świeczek/h)
- 5 dni ≈ 480 świeczek
- 1 tydzień ≈ 672 świeczki (7 dni × 96)

## Formaty Danych

### Format Bossa (domyślny)
```
<DATE>      <TIME>  <OPEN>    <HIGH>    <LOW>     <CLOSE>   <TICKVOL>
2025-10-01  00:00   24790.25  24815.50  24780.00  24800.00  1500
```
- Separator: **TAB**
- Kolumny: `<DATE>`, `<TIME>`, `<OPEN>`, `<HIGH>`, `<LOW>`, `<CLOSE>`, `<TICKVOL>`

### Format mBank
```
Time,Open,High,Low,Close
2025.10.01 00:00,24790.25,24815.50,24780.00,24800.00
```
- Separator: **semicolon** (`;`)
- Kolumna DateTime: `Time` (format: YYYY.MM.DD HH:MM)
- Brak danych volume (automatycznie ustawiane na 0)

## Hierarchiczne Linie Równoległe

System wykrywa **strukturę równoodległych poziomów** składającą się z:

- **Poziom 1**: główna linia (S1 dla LONG, R1 dla SHORT)
- **Poziomy 2, 3, 4...**: hierarchiczne linie równoległe

### Właściwości Hierarchicznych Linii

1. **Równoległość**: wszystkie linie mają identyczny slope (nachylenie)
2. **Przesunięcie pionowe**: każda linia przesunięta o offset (w punktach)
3. **Poziomy**: S2 = poziom 2 poniżej, S3 = poziom 3 poniżej, R2 = poziom 2 powyżej, itd.
4. **Score**: liczba punktów (H/L/impulsy) dotykających linii (minimum 3)

Struktura **NIE jest fraktalną** - to równomierne stepping z odległością d₁, 2×d₁, 3×d₁ (brak samopodobieństwa).

## Użycie

### Uruchomienie z config file (ZALECANE)

```bash
# Tryb days (wszystkie wykresy)
python run_support_backtest.py config_example.json

# Tryb candles (jeden wykres)
python run_support_backtest.py config_mbank.json

# Tryb candles z lookback
python run_support_backtest.py config_lookback_candles.json
```

### Przykładowe konfiguracje

**config_example.json** - tryb days, format Bossa:
```json
{
  "data_file": "FUS100.15.csv",
  "data_format": "bossa",
  "start_date": "2025-10-01",
  "end_date": "2025-10-10",
  "lookback_mode": "days",
  "lookback_days": 3,
  "generate_charts": true
}
```

**config_mbank.json** - tryb candles, format mBank:
```json
{
  "data_file": "FUS100.15_single.csv",
  "data_format": "mbank",
  "start_date": "auto",
  "end_date": "auto",
  "lookback_mode": "candles",
  "lookback_candles": 100,
  "generate_charts": true
}
```

**config_lookback_candles.json** - tryb candles, format Bossa:
```json
{
  "data_file": "FUS100.15.csv",
  "data_format": "bossa",
  "start_date": "2025-10-01",
  "end_date": "2025-10-10",
  "lookback_mode": "candles",
  "lookback_candles": 96,
  "generate_charts": true
}
```

### Podstawowe użycie (Python API)

```python
from support_breakout_strategy import SupportBreakoutStrategy
from run_support_backtest import load_data
import pandas as pd

# Wczytaj dane (auto-detect formatu)
df = load_data('FUS100.15.csv', data_format='bossa')
# lub
df = load_data('FUS100.15_single.csv', data_format='mbank')

# Utwórz strategię - tryb days
strategy = SupportBreakoutStrategy(
    lookback_mode='days',
    lookback_days=3,
    risk_pips=50,
    reward_ratio=3,
    min_slope=0.4,
    allow_descending=True,
    hierarchical_levels_below=4,
    hierarchical_levels_above=4
)

# Lub tryb candles
strategy = SupportBreakoutStrategy(
    lookback_mode='candles',
    lookback_candles=96,  # ~1 dzień dla M15
    risk_pips=50,
    reward_ratio=3,
    min_slope=0.4,
    allow_descending=True
)

# Oblicz wskaźniki (wykrywa hierarchiczne linie)
df_calc = strategy.calculate_indicators(df)

# Wyświetl hierarchiczne linie
for date, lines_list in strategy.daily_support_data.items():
    for line_info in lines_list:
        h_supp = line_info.get('hierarchical_supports', [])
        h_res = line_info.get('hierarchical_resistances', [])
        
        print(f"{date}: {len(h_supp)} wsparć, {len(h_res)} oporów")
        
        for supp in h_supp:
            print(f"  S{supp['level']}: offset={supp['offset']:+.0f}, score={supp['score']}")
        
        for res in h_res:
            print(f"  R{res['level']}: offset={res['offset']:+.0f}, score={res['score']}")
```

### Generowanie Wykresów

```python
# W trybie days: generuj wykres dla każdego dnia
for date in strategy.daily_support_data.keys():
    filename = strategy.plot_daily_chart(
        df,
        date,
        output_dir='charts',
        show_volume=True,
        mark_high_low=False
    )
    print(f"✓ {filename}")

# W trybie candles: generuj tylko jeden wykres (ostatnia data)
if strategy.lookback_mode == 'candles' and strategy.daily_support_data:
    last_date = sorted(strategy.daily_support_data.keys())[-1]
    filename = strategy.plot_daily_chart(
        df,
        last_date,
        output_dir='charts',
        show_volume=True
    )
    print(f"✓ {filename}")
```

### Backtest

```python
from backtest_engine import BacktestEngine

engine = BacktestEngine(
    initial_capital=10000,
    risk_per_trade_pct=2.0
)

results = engine.run(df, strategy, '2025-10-01', '2025-10-20')

print(f"Total Trades: {results['stats']['total_trades']}")
print(f"Win Rate: {results['stats']['win_rate']:.1f}%")
print(f"Total P&L: ${results['stats']['total_pnl']:.2f}")
```

## Struktura Danych

### daily_support_data

Każdy wpis zawiera:

```python
{
    'date': datetime.date,                      # Data analizy
    'slope': float,                             # Nachylenie głównej linii
    'intercept': float,                         # Punkt Y głównej linii
    'support_points': [{'index': int, 'price': float}],  # Punkty głównej linii
    'local_maxima': [{'index': int, 'price': float}],    # Lokalne maksima
    'all_minima': [{'index': int, 'price': float}],      # Lokalne minima
    'impulses': [{'index': int, 'price': float}],        # Impulsy
    'hierarchical_supports': [                  # Linie wsparcia poniżej S1
        {
            'slope': float,                     # Nachylenie (równoległe!)
            'intercept': float,                 # Punkt Y
            'touches': [...],                   # Punkty dotykające
            'offset': float,                    # Odległość pionowa (< 0)
            'score': int,                       # Liczba punktów (>= 3)
            'level': int                        # Numer poziomu (2, 3, 4...)
        }
    ],
    'hierarchical_resistances': [               # Linie oporu powyżej S1
        {
            'slope': float,                     # Nachylenie (równoległe!)
            'intercept': float,                 # Punkt Y
            'touches': [...],                   # Punkty dotykające
            'offset': float,                    # Odległość pionowa (> 0)
            'score': int,                       # Liczba punktów (>= 3)
            'level': int                        # Numer poziomu (2, 3, 4...)
        }
    ],
    'lookback_start_dt': datetime,              # Początek okna lookback
    'lookback_end_dt': datetime,                # Koniec okna lookback
    'day_start_idx': int                        # Index w DataFrame
}
```

## Wizualizacja

Wykresy zawierają:

- **S1**: czerwona linia ciągła (grubość 4) - główna linia wsparcia
- **S2, S3**: ciemno-czerwone linie przerywane/kropkowane (grubość 3/2)
- **R2, R3**: niebieskie linie przerywane/kropkowane (grubość 3/2)
- **Legenda**: etykiety z poziomem, offsetem i score (np. "S2 (-170 pts, 7 p)")
- **Opcjonalnie**: znaczniki lokalnych ekstremów i impulsów (mark_high_low=True)

### Kolory

- Wsparcia: `red` → `darkred` → `maroon` → `brown` → `firebrick`
- Opory: `blue` → `dodgerblue` → `deepskyblue` → `lightskyblue`

## Testy Jednostkowe

Uruchom kompleksowy zestaw testów:

```bash
# Wszystkie testy
.\tests\run_all_tests.ps1

# Testy formatów danych (Bossa/mBank + lookback modes)
python -m pytest tests/test_data_formats.py -v

# Testy strategii
python -m pytest tests/test_strategy.py -v

# Testy hierarchicznych linii
python test_support_strategy.py
```

Testy weryfikują:
1. ✅ Podstawowe wykrywanie linii wsparcia
2. ✅ Wykrywanie hierarchicznych linii równoległych
3. ✅ Równoległość wszystkich linii (identyczny slope)
4. ✅ Znaki offsetów (wsparcia < 0, opory > 0)
5. ✅ Strukturę danych (wymagane klucze, typy, zakresy)
6. ✅ Generowanie wykresów z hierarchicznymi liniami
7. ✅ **Format Bossa** (TSV, kolumny `<DATE>`, `<TIME>`, etc.)
8. ✅ **Format mBank** (CSV semicolon, kolumna `Time`)
9. ✅ **Auto-detection dat** z obu formatów
10. ✅ **Tryb lookback_days** (dni handlowe)
11. ✅ **Tryb lookback_candles** (liczba świeczek)

**Status testów:** 10/10 modułów PASSED ✅

## Parametry Strategii

```python
SupportBreakoutStrategy(
    # Lookback window
    lookback_mode='days',       # 'days' lub 'candles'
    lookback_days=5,            # Liczba dni (dla mode='days')
    lookback_candles=96,        # Liczba świeczek (dla mode='candles')
    
    # Risk management
    risk_pips=50,               # Ryzyko SL w pipsach
    reward_ratio=3,             # R:R ratio dla TP
    
    # Breakout mode
    retest_mode=False,          # False=immediate, True=czeka na retest
    retest_tolerance=30,        # Odległość od linii dla retest (pips)
    
    # Line detection
    min_slope=0.1,              # Minimalny |slope| (bezwzględna wartość)
    allow_descending=True,      # Wykrywaj linie opadające (SHORT)
    
    # Hierarchical levels
    hierarchical_levels_below=4,
    hierarchical_levels_above=4,
    hierarchical_tolerance=30,
    
    # Visualization
    show_legend=True,
    chart_dpi=150,
    
    # Trading rules
    close_at_eod=False          # Zamykaj pozycje na koniec dnia
)
```

### Dostrajanie

**Lookback:**
- `lookback_days`: 3-7 dni (krótszy = więcej linii, dłuższy = stabilniejsze)
- `lookback_candles`: 96-480 świeczek dla M15 (96 = 1 dzień, 480 = 5 dni)
- `lookback_mode='candles'`: zalecane dla backtestingu intraday

**Slope:**
- `min_slope`: 0.1-0.5 (wyższy = tylko silne trendy)
- `allow_descending=true`: wykrywa linie opadające (SHORT)

**Risk:**
- `risk_pips`: 20-100 (zależne od instrumentu i volatility)
- `reward_ratio`: 2-5 (wyższy = większy potencjał, mniej TP)

**Data:**
- `start_date/end_date="auto"`: automatyczne wykrywanie z pliku
- `data_format="bossa"`: dla plików TSV z Bossa
- `data_format="mbank"`: dla plików CSV z mBank

## Integracja z impulse_detector

Strategia używa `impulse_detector.py` do:
- Wykrywania impulsów (7 kryteriów)
- Znajdowania lokalnych ekstremów
- **Wykrywania hierarchicznych linii równoległych** (`find_hierarchical_parallel_lines()`)

Hierarchiczne linie wykrywane są automatycznie z parametrami:
- `num_levels_below=2` - 2 linie wsparcia poniżej S1
- `num_levels_above=2` - 2 linie oporu powyżej S1
- `tolerance=30` - max odległość punktu od linii (punkty)
- `debug=False` - wyłączone logi debugowe (zbyt dużo outputu)

## Przykładowe Wyniki

Na danych FUS100.15 (październik 2025):

```
2025-10-06: 2 wsparć poniżej, 1 oporów powyżej
  - S2: offset=-170, score=7
  - S3: offset=-70, score=6
  - R2: offset=+60, score=5

2025-10-15: 2 wsparć poniżej, 2 oporów powyżej
  - S2: offset=-100, score=6
  - S3: offset=-260, score=4
  - R2: offset=+60, score=6
  - R3: offset=+60, score=3
```

## Znane Ograniczenia

1. **Forward-looking bias**: weryfikacja patrzy w przyszłość (nie real-time)
2. **Tryb candles**: generuje tylko jeden wykres (ostatnia data), idealny dla backtestingu
3. **Tryb days**: generuje wykres dla każdego dnia (może być wolne dla długich okresów)
4. **Performance**: dla dużych zakresów (>10k świec) może być wolne
5. **Tolerance**: wymaga dostrojenia do instrumentu (20-50 pkt dla indeksów)
6. **Format mBank**: brak danych volume (ustawiane automatycznie na 0)

## TODO

- [ ] Detekcja typu trójkąta (zbieżny vs rozszerzający - szerokość kanału)
- [ ] Filtr: pomiń zbieżne, traduj tylko rozszerzające
- [ ] Walidacja 5 warunków wejścia dla rozszerzającego
- [ ] Real-time mode bez forward-looking bias
- [ ] Optymalizacja performance (vectorization)
- [ ] Export wyników do JSON/CSV

## Licencja

MIT License

## Autor

AI FX Trading System  
Version: 2.1  
Date: 2025-11-23

**Changelog:**
- **v2.1** (2025-11-23): Dodano tryb lookback_candles, formaty Bossa/mBank, auto-detection dat
- **v2.0** (2025-11-12): Hierarchiczne linie równoległe, pozycje SHORT, refactoring
- **v1.0** (2025-10-01): Pierwsza wersja z podstawowym wykrywaniem linii support

---

**Podsumowanie**: Support Breakout Strategy z hierarchicznymi liniami równoległymi to zaawansowany system wykrywający strukturę równoodległych poziomów (S1, S2, S3, R2, R3) z wizualizacją, testami i integracją z impulse_detector. System obsługuje dwa tryby lookback (days/candles), dwa formaty danych (Bossa/mBank) i auto-detection dat. Wszystkie linie są równoległe (ten sam slope) i opisane offsetem i score. System gotowy do użycia w backtestingu i analizie technicznej.
