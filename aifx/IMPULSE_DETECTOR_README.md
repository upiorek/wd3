# Impulse Detector - Dokumentacja

## Przegląd

`impulse_detector.py` implementuje strategię **Multi-Level Impulse Breakout** do wykrywania:
1. **Impulsów rynkowych** - momenty ekstremalnego zaangażowania (7 kryteriów)
2. **Lokalnych ekstremów** - High/Low punkty (H/L)
3. **Hierarchicznych równoległych linii wsparcia/oporu** - poziomy 1, 2, 3+

## Kluczowe koncepcje

### Równoległość linii
- **Wszystkie linie wsparcia (S1, S2, S3...) są równoległe między sobą**
- **Wszystkie linie oporu (R1, R2, R3...) są równoległe między sobą**
- **Nachylenie support i resistance: symetrycznie odbite**
  ```
  slope_resistance = -slope_support
  |slope_R| = |slope_S| (ale przeciwne znaki)
  ```

### Hierarchia poziomów

```
R3 ============================================  (poziom 3, +2d₁)
R2 ---------------------------                  (poziom 2, +d₁)
R1 ━━━━━━━━━━━━━━━━━━━━━━━━━━━ (GŁÓWNA LINIA)   (poziom 1, 0)
S1 ━━━━━━━━━━━━━━━━━━━━━━━━━━━ (GŁÓWNA LINIA)   (poziom 1, 0)
S2 ---------------------------                  (poziom 2, -d₁)
S3 ============================================  (poziom 3, -2d₁)
```

**Odległość pionowa między poziomami:**
- Poziom 1 → 2: d₁ (odległość bazowa)
- Poziom 2 → 3: d₂ ≈ d₁ (równomierne stepping)
- Poziom 3 → 4: d₃ ≈ d₁

**To NIE jest prawdziwa fraktalność** (brak samopodobieństwa), ale struktura równoodległa.

### Nachylenie i czas

Linie mają nachylenie (slope ≠ 0), więc **wraz z upływem czasu oczekiwana cena zmienia się**:

- Trend wzrostowy (slope > 0): im dalej w czasie, tym wyższe poziomy cenowe
- Trend spadkowy (slope < 0): im dalej w czasie, tym niższe poziomy cenowe
- **Odległość "d" to przesunięcie pionowe**, ale rzeczywista cena zależy od czasu

## Główne funkcje

### 1. `find_support_trendline(df, extrema, impulses, tolerance=30)`

Znajduje **główną linię wsparcia** (poziom 1) przechodzącą przez:
- Lokalne minima (L) gdzie cena dotyka linii
- Impulsy (I) przy testowaniu wsparcia

**Parametry:**
- `df`: DataFrame z OHLCV
- `extrema`: DataFrame z H/L punktami
- `impulses`: DataFrame z impulsami
- `tolerance`: max odległość punktu od linii (punkty)

**Zwraca:**
```python
{
    'slope': float,          # nachylenie linii
    'intercept': float,      # punkt przecięcia Y
    'touches': list,         # punkty dotykające linii
    'bounces': int,          # liczba odbić
    'dynamic_breaks': int,   # dynamiczne przebicia
    'score': float          # ocena jakości linii
}
```

### 2. `find_hierarchical_parallel_lines(df, base_line, extrema, impulses, num_levels_below=2, num_levels_above=2, tolerance=30, debug=True)`

Znajduje **hierarchiczne równoległe linie** powyżej i poniżej głównej.

**Parametry:**
- `df`: DataFrame z OHLCV
- `base_line`: główna linia (dict z 'slope', 'intercept')
- `extrema`: DataFrame z H/L
- `impulses`: DataFrame z impulsami
- `num_levels_below`: ile linii wsparcia poniżej głównej (domyślnie 2)
- `num_levels_above`: ile linii oporu powyżej głównej (domyślnie 2)
- `tolerance`: max odległość punktu od linii (domyślnie 30)
- `debug`: czy wyświetlać informacje debugowe (domyślnie True)

**Zwraca:**
```python
(support_lines_below, resistance_lines_above)
```

Każda linia to dict:
```python
{
    'slope': float,         # nachylenie (równoległe do głównej)
    'intercept': float,     # przesunięcie Y
    'touches': list,        # punkty dotykające
    'offset': float,        # odległość pionowa od głównej (+/-)
    'score': int,          # liczba punktów na linii
    'level': int           # numer poziomu (2, 3, 4, ...)
}
```

**Algorytm:**
1. Zaczyna od głównej linii (poziom 1)
2. Filtruje punkty **powyżej** głównej (dla oporów)
3. Szuka najlepszej równoległej linii (max punktów w tolerance)
4. Usuwa użyte punkty
5. Powtarza dla kolejnego poziomu (używając nowej linii jako reference)
6. Analogicznie dla linii **poniżej** (wsparcia)

### 3. `detect_impulse_points(df, min_periods=20, forward_candles=15, min_profit_points=80)`

Wykrywa punkty impulsu z **weryfikacją wyniku**.

**7 kryteriów impulsu:**
1. Momentum candle - duża świeca w górę
2. Wzrost wolumenu (+50%+)
3. Breakout z konsolidacji (ATR expansion)
4. Odbicie od EMA20 (pullback)
5. Higher high formation
6. Retest wsparcia (poprzedni opór)
7. **Weryfikacja: czy nastąpił wzrost >= min_profit_points**

**Parametry:**
- `forward_candles`: ile świec do przodu sprawdzamy (domyślnie 15 = ~4h na M15)
- `min_profit_points`: minimalny wzrost aby uznać sygnał (domyślnie 80)

**Zwraca:**
DataFrame z kolumnami:
```python
{
    'datetime': timestamp,
    'price': entry_price,
    'score': float,              # siła sygnału
    'reasons': str,              # powody (7 kryteriów)
    'profit_achieved': float,    # faktyczny profit
    'max_drawdown': float,       # max spadek
    'rr_ratio': float           # risk/reward ratio
}
```

### 4. `find_local_extrema(df, order=5)`

Znajduje lokalne minima i maksima używając `scipy.signal.argrelextrema`.

**Parametry:**
- `order`: ile świec po obu stronach musi być wyższych/niższych (domyślnie 5)

**Zwraca:**
DataFrame:
```python
{
    'index': int,
    'datetime': timestamp,
    'price': float,
    'type': 'maximum' lub 'minimum'
}
```

### 5. `plot_with_impulses(csv_file, start_date, end_date, output_file, top_n=4, min_profit=40)`

Generuje wykres z zaznaczonymi:
- Impulsami (zielone okręgi)
- Ekstremami H/L (niebieskie okręgi)
- Główną linią wsparcia S1 (czerwona ciągła, gruba)
- Liniami wsparcia S2, S3... (czerwone przerywane/kropkowane)
- Liniami oporu R2, R3... (niebieskie przerywane/kropkowane)

**Kolory linii:**
- **S1**: czerwony, ciągły, grubość 4
- **S2**: ciemnoczerwony, `--`, grubość 3
- **S3+**: brązowe odcienie, `:`, grubość 2
- **R2**: niebieski, `--`, grubość 3
- **R3+**: jaśniejsze niebieskie, `:`, grubość 2

**Znaczniki punktów:**
- Główna linia: okrąg `o`
- Wsparcia niższe: kwadrat `s`
- Opory wyższe: trójkąt `^`

## Użycie

### Analiza z domyślnymi parametrami

```bash
python impulse_detector.py
```

Domyślnie analizuje: 2025-09-28 do 2025-10-02

### Analiza dla konkretnego zakresu dat

```bash
python impulse_detector.py 2025-10-01 2025-10-31
```

Wygeneruje plik: `impulse_analysis_2025-10-01_to_2025-10-31.png`

### Uruchomienie testów

```bash
python impulse_detector.py --test
```

Test weryfikuje:
- Poprawność struktury zwracanych danych
- Równoległość linii (slope taki sam)
- Znaki offsetów (powyżej +, poniżej -)
- Obecność wszystkich wymaganych kluczy

## Przykład wyjścia (logi)

```
=== find_hierarchical_parallel_lines DEBUG ===
Punktów H/L: 45, Impulsów: 12, Razem: 57
Główna linia: slope=2.345678, intercept=20123.45
Szukam 2 poziomów powyżej i 2 poniżej

--- Szukam linii wsparcia PONIŻEJ głównej ---
  Poziom 2 (below): kandydatów punktów = 23
    Offset -60: 4 punktów (NEW BEST)
    Offset -70: 5 punktów (NEW BEST)
  ✓ Znaleziono linię poziomu 2: offset=-70, score=5

  Poziom 3 (below): kandydatów punktów = 18
    Offset -140: 3 punktów (NEW BEST)
  ✓ Znaleziono linię poziomu 3: offset=-140, score=3

--- Szukam linii oporu POWYŻEJ głównej ---
  Poziom 2 (above): kandydatów punktów = 19
    Offset +80: 6 punktów (NEW BEST)
  ✓ Znaleziono linię poziomu 2: offset=+80, score=6

  Poziom 3 (above): kandydatów punktów = 13
  ✗ Nie znaleziono linii poziomu 3 (min 3 punkty)

=== WYNIK: 1 linii oporu, 2 linii wsparcia ===
```

## Wymagania

```
pandas
numpy
matplotlib
mplfinance
scipy
```

Instalacja:
```bash
pip install pandas numpy matplotlib mplfinance scipy
```

## Struktura pliku CSV

Plik wejściowy (np. `FUS100.15.csv`):
```
Date	Time	Open	High	Low	Close	TickVol	Vol	Spread
2025-09-28	00:00	20123.45	20145.67	20100.23	20130.00	1234	0	15
...
```

Format:
- Separator: TAB (`\t`)
- Pierwsza linia: nagłówek (pomijany przez `skiprows=1`)
- Kolumny: Date, Time, Open, High, Low, Close, TickVol, Vol, Spread

## Output

Wykres PNG zawiera:
- Świeczki (candlestick)
- Wolumen (volume bar chart)
- EMA20 (pomarańczowa linia)
- EMA50 (niebieska linia)
- **Impulsy**: zielone okręgi + score
- **Ekstrema H**: niebieskie okręgi + tekst "H"
- **Ekstrema L**: niebieskie okręgi + tekst "L"
- **Hierarchiczne linie**: S1, S2, S3, R2, R3 (równoległe)
- **Legenda**: poziomy z offsetami i liczbą punktów

## Testy jednostkowe

```python
def test_hierarchical_lines():
    """
    Tworzy syntetyczne dane:
    - 100 świec z trendem wzrostowym (slope ~ 5)
    - 10 ekstremów (co 10 świec)
    - 15 impulsów (co 7 świec)
    
    Weryfikuje:
    - Zwracane typy (listy)
    - Strukturę danych (słowniki z kluczami)
    - Równoległość linii (slope identyczne)
    - Znaki offsetów (+ dla oporu, - dla wsparcia)
    - Numery poziomów
    """
```

## Najlepsze praktyki

1. **Tolerance**: Dostosuj do volatilności instrumentu
   - Forex: 20-40 pips
   - Indeksy (Nasdaq): 30-50 punktów
   - Akcje: 0.5-2% ceny

2. **Num levels**: 
   - `num_levels_above=2-3` (opory)
   - `num_levels_below=2-3` (wsparcia)
   - Więcej poziomów = więcej noise

3. **Debug mode**:
   - Włącz (`debug=True`) podczas developmentu
   - Wyłącz w produkcji dla performance

4. **Min profit**:
   - Zwiększ dla mniej sygnałów, ale lepszej jakości
   - Zmniejsz dla więcej okazji, ale z większym ryzykiem

## Znane ograniczenia

1. **Wymaga danych historycznych** - nie działa real-time
2. **Forward-looking bias** - weryfikacja impulsów patrzy w przyszłość
3. **Parametr tolerance** - wymaga tuningu dla każdego instrumentu
4. **Performance** - wolny dla bardzo dużych zakresów (>10k świec)

## TODO

- [ ] Detekcja typu trójkąta (zbieżny vs rozszerzający)
- [ ] Filtr: pomiń zbieżne, traduj tylko rozszerzające
- [ ] Walidacja 5 warunków wejścia
- [ ] Real-time mode (bez forward-looking)
- [ ] Optymalizacja performance (vectorization)
- [ ] Export do JSON/CSV

## Autor

aifx strategy implementation  
Wersja: 2.0 (hierarchiczne linie równoległe)  
Data: 2025-11-12

## Licencja

Internal use only - strategia proprietary.
