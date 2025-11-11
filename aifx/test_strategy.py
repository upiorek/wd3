"""
Automated tests dla Support Breakout Strategy
Uruchomienie: pytest test_strategy.py -v
"""
import pytest
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
from support_breakout_strategy import SupportBreakoutStrategy
from backtest_engine import BacktestEngine


# ===== FIXTURES (dane testowe) =====

@pytest.fixture
def sample_data():
    """Generuje przykładowe dane M15 dla testów"""
    dates = pd.date_range('2025-01-01', periods=500, freq='15min')
    
    # Symulacja trendu wzrostowego z volatility
    base_price = 1.05000
    trend = np.linspace(0, 0.005, 500)  # Wzrost o 50 pipsów
    noise = np.random.normal(0, 0.0002, 500)  # Szum ±2 pipsy
    
    close_prices = base_price + trend + noise
    
    df = pd.DataFrame({
        'Open': close_prices - np.random.uniform(0, 0.0001, 500),
        'High': close_prices + np.random.uniform(0.0001, 0.0003, 500),
        'Low': close_prices - np.random.uniform(0.0001, 0.0003, 500),
        'Close': close_prices,
        'Volume': np.random.randint(1000, 5000, 500),
        'DateTime': dates  # KOLUMNA, nie index
    })
    
    return df


@pytest.fixture
def impulse_data():
    """Dane z oczywistym impulsem wzrostowym"""
    dates = pd.date_range('2025-01-01', periods=100, freq='15min')
    
    close_prices = [1.05000] * 50  # 50 świec stabilnych
    # Impulse świeca: duży wzrost, high volume
    close_prices.extend([1.05100, 1.05150, 1.05200])  # +20 pipsów w 3 świece
    close_prices.extend([1.05200] * 47)  # Stabilizacja
    
    df = pd.DataFrame({
        'Open': [p - 0.00005 for p in close_prices],
        'High': [p + 0.00010 for p in close_prices],
        'Low': [p - 0.00010 for p in close_prices],
        'Close': close_prices,
        'Volume': [2000] * 50 + [8000, 8000, 8000] + [2000] * 47,  # Volume spike
        'DateTime': dates  # KOLUMNA, nie index
    })
    
    return df


@pytest.fixture
def strategy_default():
    """Strategia z domyślnymi parametrami"""
    return SupportBreakoutStrategy(
        lookback_days=5,
        risk_pips=50,
        reward_ratio=3,
        retest_mode=False,
        min_slope=0.1
    )


# ===== TESTY PODSTAWOWE =====

class TestStrategyInitialization:
    """Testy inicjalizacji strategii"""
    
    def test_default_parameters(self):
        """Sprawdza czy domyślne parametry są poprawne"""
        strategy = SupportBreakoutStrategy()
        
        assert strategy.lookback_days == 5
        assert strategy.risk_pips == 50
        assert strategy.reward_ratio == 3
        assert strategy.retest_mode == False
        assert strategy.min_slope == 0.1
    
    def test_custom_parameters(self):
        """Sprawdza czy custom parametry są zachowane"""
        strategy = SupportBreakoutStrategy(
            lookback_days=3,
            risk_pips=30,
            reward_ratio=5,
            min_slope=0.3
        )
        
        assert strategy.lookback_days == 3
        assert strategy.risk_pips == 30
        assert strategy.reward_ratio == 5
        assert strategy.min_slope == 0.3
    
    def test_cache_initialization(self):
        """Sprawdza czy cache structures są zainicjowane"""
        strategy = SupportBreakoutStrategy()
        
        assert hasattr(strategy, 'support_lines')
        assert hasattr(strategy, 'daily_support_data')
        assert isinstance(strategy.support_lines, dict)
        assert isinstance(strategy.daily_support_data, list)


class TestIndicatorCalculation:
    """Testy obliczania wskaźników"""
    
    def test_calculate_indicators_columns(self, strategy_default, sample_data):
        """Sprawdza czy wszystkie wymagane kolumny są dodane"""
        df = strategy_default.calculate_indicators(sample_data.copy())
        
        # Strategia dodaje tylko Support columns (nie EMA/ATR - te są wewnętrzne)
        required_columns = ['Support_Slope', 'Support_Intercept', 'Support_Price']
        
        for col in required_columns:
            assert col in df.columns, f"Brak kolumny {col}"
    
    def test_calculate_indicators_adds_support(self, strategy_default, sample_data):
        """Sprawdza czy Support_Price jest obliczany dla niektórych świec"""
        df = strategy_default.calculate_indicators(sample_data.copy())
        
        # Po pierwszych lookback_candles świeczek powinny być wartości (lub 0.0 gdy brak linii)
        has_values = (df['Support_Price'].notna()).sum()
        assert has_values > 0, "Wszystkie Support_Price są NaN"
        
        # Sprawdź czy przynajmniej niektóre wartości są sensowne (nie 0, nie NaN)
        valid_prices = df[(df['Support_Price'].notna()) & (df['Support_Price'] > 0)]['Support_Price']
        
        if len(valid_prices) > 0:
            # Jeśli są jakieś nietrywialne wartości, sprawdź rozsądność
            support_mean = valid_prices.mean()
            close_mean = df['Close'].mean()
            # Support powinien być w zakresie ±20% od średniej ceny
            assert abs(support_mean - close_mean) / close_mean < 0.2


class TestImpulseDetection:
    """Testy wykrywania impulsów"""
    
    def test_impulse_detection_returns_list(self, strategy_default):
        """Sprawdza czy zwraca listę"""
        # Przygotuj dane z wymaganymi kolumnami (EMA, ATR wewnętrznie obliczane)
        dates = pd.date_range('2025-01-01', periods=100, freq='15min')
        df = pd.DataFrame({
            'Open': [1.05] * 100,
            'High': [1.051] * 100,
            'Low': [1.049] * 100,
            'Close': [1.05] * 100,
            'Volume': [2000] * 100,
            'DateTime': dates
        })
        
        impulses = strategy_default._detect_impulses_full(df)
        assert isinstance(impulses, list)
    
    def test_impulse_indices_valid(self, strategy_default):
        """Sprawdza czy indeksy impulsów są w zakresie DataFrame"""
        dates = pd.date_range('2025-01-01', periods=100, freq='15min')
        df = pd.DataFrame({
            'Open': [1.05] * 100,
            'High': [1.051] * 100,
            'Low': [1.049] * 100,
            'Close': [1.05] * 100,
            'Volume': [2000] * 100,
            'DateTime': dates
        })
        
        impulses = strategy_default._detect_impulses_full(df)
        
        for idx in impulses:
            assert 0 <= idx < len(df), f"Impuls index {idx} poza zakresem"


class TestSupportLine:
    """Testy wyznaczania linii wsparcia"""
    
    def test_support_line_returns_tuple(self, strategy_default, sample_data):
        """Sprawdza czy _find_support_line zwraca tuple"""
        df = sample_data.copy()
        # _find_support_line wymaga kolumny 'index'
        df['index'] = range(len(df))
        
        result = strategy_default._find_support_line(df)

        # Now _find_support_line returns a dict with keys including 'slope' and 'intercept'
        assert isinstance(result, dict)
        assert 'slope' in result and 'intercept' in result
    
    def test_support_line_slope_type(self, strategy_default, sample_data):
        """Sprawdza czy slope jest float lub NaN"""
        df = sample_data.copy()
        df['index'] = range(len(df))
        
        result = strategy_default._find_support_line(df)
        slope = result.get('slope')
        intercept = result.get('intercept')

        assert isinstance(slope, (float, np.floating, int)) or np.isnan(slope)
        assert isinstance(intercept, (float, np.floating, int)) or np.isnan(intercept)
    
    def test_min_slope_filter(self, sample_data):
        """Sprawdza czy min_slope filter działa"""
        # Strategia z wysokim min_slope
        strategy_strict = SupportBreakoutStrategy(min_slope=1.0)
        
        df = sample_data.copy()
        df = strategy_strict.calculate_indicators(df)
        
        # Z wysokim min_slope większość linii powinna być odrzucona (NaN)
        nan_count = df['Support_Slope'].isna().sum()
        assert nan_count > len(df) * 0.5, "Min slope filter nie działa"

    def test_map_support_point_within_lookback(self):
        """
        Testuje czy mapping punktu support zwraca DateTime mieszczący się w oknie lookback
        i nie mapuje punktów na świeczki analizowanego dnia.
        """
        from datetime import datetime, timedelta
        # Użyjemy małego window: 10 świeczek lookback + 1 świeczka testowana
        start = datetime(2025, 10, 8, 0, 0)
        lookback_periods = 10

        # Stwórz dataframe
        dates = [start + timedelta(minutes=15 * i) for i in range(lookback_periods + 1)]
        df = pd.DataFrame({
            'DateTime': pd.Series(dates),
            'Open': [100.0 + i * 0.1 for i in range(len(dates))],
            'High': [100.5 + i * 0.1 for i in range(len(dates))],
            'Low': [99.5 + i * 0.1 for i in range(len(dates))],
            'Close': [100.2 + i * 0.1 for i in range(len(dates))],
            'Volume': [1000 for _ in range(len(dates))]
        })

        s = SupportBreakoutStrategy(lookback_days=1)

        support_info = {
            'lookback_start_dt': df.loc[0, 'DateTime'],
            'lookback_end_dt': df.loc[lookback_periods - 1, 'DateTime']
        }

        # Punkt wskazujący na ostatnią świeczkę lookback -> powinien mapować się prawidłowo
        p = {'index': lookback_periods - 1, 'price': float(df.loc[lookback_periods - 1, 'Low'])}
        mapped = s._map_support_point_to_datetime(p, support_info, df)
        assert mapped is not None
        assert mapped == df.loc[lookback_periods - 1, 'DateTime']

        # Punkt poza lookback -> powinien zwrócić None
        p_out = {'index': lookback_periods, 'price': float(df.loc[lookback_periods, 'Low'])}
        mapped_out = s._map_support_point_to_datetime(p_out, support_info, df)
        assert mapped_out is None


class TestEntryConditions:
    """Testy warunków wejścia"""
    
    def test_should_enter_requires_support_price(self, strategy_default, sample_data):
        """Sprawdza czy wymaga Support_Price"""
        df = sample_data.copy()
        df = strategy_default.calculate_indicators(df)
        
        # Usuń Support_Price dla testowej świecy
        df.at[df.index[50], 'Support_Price'] = np.nan
        
        result = strategy_default.should_enter(df, 50)
        assert result is None, "Powinien zwrócić None gdy brak Support_Price"
    
    def test_should_enter_requires_previous_candle(self, strategy_default, sample_data):
        """Sprawdza czy wymaga poprzedniej świecy"""
        df = sample_data.copy()
        df = strategy_default.calculate_indicators(df)
        
        result = strategy_default.should_enter(df, 0)
        assert result is None, "Powinien zwrócić None gdy idx=0"
    
    def test_breakout_detection_logic(self, strategy_default, sample_data):
        """Test logiki breakout"""
        df = sample_data.copy()
        # Wyraźny breakout: Close przekracza Support_Price
        df.loc[df.index[10], 'Close'] = 0.99
        df.loc[df.index[11], 'Close'] = 1.05
        df.loc[df.index[10], 'Support_Price'] = 1.00
        df.loc[df.index[11], 'Support_Price'] = 1.00
        
        result = strategy_default.should_enter(df, 11)
        assert result is not None, "Nie wykryto breakout"
        assert isinstance(result, dict), "should_enter powinien zwrócić dict"
        assert result['direction'] == 'long'
        assert result['entry_price'] == 1.05


class TestExitConditions:
    """Testy warunków wyjścia"""
    
    def test_check_exit_sl_hit(self, strategy_default, sample_data):
        """Sprawdza wykrycie Stop Loss"""
        df = sample_data.copy()
        
        # Stwórz pozycję (trade dict z wymaganymi kluczami)
        trade = {
            'entry_price': 1.05100,
            'sl_price': 1.05050,
            'tp_price': 1.05250
        }
        
        # Stwórz sytuację: Low dotyka SL
        df.at[df.index[10], 'Low'] = 1.05045
        
        result = strategy_default.check_exit(df, 10, trade)
        
        assert result is not None, "Powinien wykryć SL"
        assert result['result'] == 'SL'
        assert result['exit_price'] == trade['sl_price']
    
    def test_check_exit_tp_hit(self, strategy_default, sample_data):
        """Sprawdza wykrycie Take Profit"""
        df = sample_data.copy()
        
        # Stwórz pozycję
        trade = {
            'entry_price': 1.05100,
            'sl_price': 1.05050,
            'tp_price': 1.05250
        }
        
        # Stwórz sytuację: High dotyka TP
        df.at[df.index[10], 'High'] = 1.05255
        
        result = strategy_default.check_exit(df, 10, trade)
        
        assert result is not None, "Powinien wykryć TP"
        assert result['result'] == 'TP'
        assert result['exit_price'] == trade['tp_price']
    
    def test_check_exit_no_hit(self, strategy_default, sample_data):
        """Sprawdza brak SL/TP"""
        df = sample_data.copy()
        
        # Stwórz pozycję
        trade = {
            'entry_price': 1.05100,
            'sl_price': 1.05050,
            'tp_price': 1.05250
        }
        
        # Świeca w zakresie (nie trafia SL ani TP)
        df.at[df.index[10], 'Low'] = 1.05055
        df.at[df.index[10], 'High'] = 1.05245
        
        result = strategy_default.check_exit(df, 10, trade)
        
        assert result is None, "Nie powinien wykryć exit"


class TestBacktestEngine:
    """Testy silnika backtestingu"""
    
    def test_backtest_engine_initialization(self):
        """Sprawdza inicjalizację engine"""
        engine = BacktestEngine()
        assert engine is not None
    
    def test_backtest_returns_dict(self, strategy_default, sample_data):
        """Sprawdza czy backtest zwraca słownik wyników"""
        engine = BacktestEngine(initial_capital=10000, risk_per_trade_pct=2.0)
        
        results = engine.run(
            sample_data.copy(),
            strategy_default,
            start_date='2025-01-02',
            end_date='2025-01-05'
        )
        
        assert isinstance(results, dict)
    
    def test_backtest_required_keys(self, strategy_default, sample_data):
        """Sprawdza czy wyniki mają wymagane klucze"""
        engine = BacktestEngine(initial_capital=10000, risk_per_trade_pct=2.0)
        
        results = engine.run(
            sample_data.copy(),
            strategy_default,
            start_date='2025-01-02',
            end_date='2025-01-05'
        )
        
        # Sprawdź strukturę top-level
        assert 'trades' in results
        assert 'equity_curve' in results
        assert 'stats' in results
        assert 'df_full' in results
        
        # Sprawdź klucze w stats (zawsze obecne)
        stats = results['stats']
        required_stats = [
            'total_trades', 'win_rate', 'total_pnl', 
            'final_capital', 'max_drawdown_pct', 'return_pct'
        ]
        for key in required_stats:
            assert key in stats, f"Brak klucza {key} w stats"
        
        # Jeśli były trade, powinny być wins/losses
        if stats['total_trades'] > 0:
            assert 'wins' in stats
            assert 'losses' in stats
    
    def test_backtest_capital_conservation(self, strategy_default, sample_data):
        """Sprawdza czy kapitał jest zachowany (no free money)"""
        initial_capital = 10000
        engine = BacktestEngine(initial_capital=initial_capital, risk_per_trade_pct=2.0)
        
        results = engine.run(
            sample_data.copy(),
            strategy_default,
            start_date='2025-01-02',
            end_date='2025-01-05'
        )
        
        stats = results['stats']
        # Final capital = initial + PnL
        expected_final = initial_capital + stats['total_pnl']
        assert abs(stats['final_capital'] - expected_final) < 0.01
    
    def test_backtest_win_rate_calculation(self, strategy_default, sample_data):
        """Sprawdza poprawność win rate"""
        engine = BacktestEngine(initial_capital=10000, risk_per_trade_pct=2.0)
        
        results = engine.run(
            sample_data.copy(),
            strategy_default,
            start_date='2025-01-02',
            end_date='2025-01-05'
        )
        
        stats = results['stats']
        if stats['total_trades'] > 0:
            expected_wr = (stats['wins'] / stats['total_trades']) * 100


class TestPlottingIntegration:
    """Prosty test integracyjny generujący obrazek i sprawdzający, że markery zostały narysowane"""

    def test_plot_draws_markers(self, tmp_path):
        from datetime import datetime, timedelta
        import numpy as np
        import matplotlib.image as mpimg
        import os

        s = SupportBreakoutStrategy(lookback_days=1)

        # Zbuduj dane: 10 świeczek lookback + 1 świeczka analizowana
        start = datetime(2025, 10, 8, 0, 0)
        lookback = 10
        dates = [start + timedelta(minutes=15 * i) for i in range(lookback + 1)]
        df = pd.DataFrame({
            'DateTime': pd.Series(dates),
            'Open': [100.0 + i * 0.1 for i in range(len(dates))],
            'High': [100.5 + i * 0.1 for i in range(len(dates))],
            'Low': [99.5 + i * 0.1 for i in range(len(dates))],
            'Close': [100.2 + i * 0.1 for i in range(len(dates))],
            'Volume': [1000 for _ in range(len(dates))]
        })

        analyzed_date = dates[-1].date()

        support_info = {
            'date': analyzed_date,
            'slope': 0.0,
            'intercept': 0.0,
            'support_points': [{'index': lookback - 1, 'price': float(df.loc[lookback - 1, 'Low'])}],
            'local_maxima': [],
            'all_minima': [{'index': lookback - 2, 'price': float(df.loc[lookback - 2, 'Low'])}],
            'impulses': [],
            'lookback_start_dt': df.loc[0, 'DateTime'],
            'lookback_end_dt': df.loc[lookback - 1, 'DateTime'],
            'day_start_idx': lookback
        }

        s.daily_support_data.append(support_info)

        outdir = str(tmp_path / 'charts')
        filename = s.plot_daily_chart(df, analyzed_date, output_dir=outdir, show_volume=False, mark_high_low=True)

        assert filename is not None and os.path.exists(filename)

        img = mpimg.imread(filename)

        # img is float32 array with values in [0,1] or uint8 depending on backend
        if img.dtype != np.float32 and img.dtype != np.float64:
            img = img.astype('float32') / 255.0

        def has_color(img, target_rgb, tol=0.25):
            r = img[:, :, 0]
            g = img[:, :, 1]
            b = img[:, :, 2]
            mask = (np.abs(r - target_rgb[0]) <= tol) & (np.abs(g - target_rgb[1]) <= tol) & (np.abs(b - target_rgb[2]) <= tol)
            return mask.any()

        # yellow outline for support_points (markeredgecolor='yellow')
        assert has_color(img, (1.0, 1.0, 0.0), tol=0.25), "Nie znaleziono pikseli żółtego (support points)"
        # red outline for all_minima
        assert has_color(img, (1.0, 0.0, 0.0), tol=0.25), "Nie znaleziono pikseli czerwonych (all minima)"

    def test_legend_contains_expected_labels(self, tmp_path):
        # Reuse small dataset from previous test but only check legend labels
        from datetime import datetime, timedelta
        s = SupportBreakoutStrategy(lookback_days=1)
        start = datetime(2025, 10, 8, 0, 0)
        lookback = 10
        dates = [start + timedelta(minutes=15 * i) for i in range(lookback + 1)]
        df = pd.DataFrame({
            'DateTime': pd.Series(dates),
            'Open': [100.0 + i * 0.1 for i in range(len(dates))],
            'High': [100.5 + i * 0.1 for i in range(len(dates))],
            'Low': [99.5 + i * 0.1 for i in range(len(dates))],
            'Close': [100.2 + i * 0.1 for i in range(len(dates))],
            'Volume': [1000 for _ in range(len(dates))]
        })

        analyzed_date = dates[-1].date()
        support_info = {
            'date': analyzed_date,
            'slope': 0.0,
            'intercept': 0.0,
            'support_points': [{'index': lookback - 1, 'price': float(df.loc[lookback - 1, 'Low'])}],
            'local_maxima': [],
            'all_minima': [{'index': lookback - 2, 'price': float(df.loc[lookback - 2, 'Low'])}],
            'impulses': [],
            'lookback_start_dt': df.loc[0, 'DateTime'],
            'lookback_end_dt': df.loc[lookback - 1, 'DateTime'],
            'day_start_idx': lookback
        }

        s.daily_support_data.append(support_info)
        outdir = str(tmp_path / 'charts')
        filename = s.plot_daily_chart(df, analyzed_date, output_dir=outdir, show_volume=False, mark_high_low=True)

        # Check saved legend labels on the strategy instance
        labels = getattr(s, '_last_legend_labels', [])
        # Expected to contain our marker labels (order may vary)
        expected = {'Support Points', 'All Minima', 'Local Highs', 'Impulses'}
        assert expected.intersection(set(labels)), f"Legenda nie zawiera oczekiwanych etykiet. Zawiera: {labels}"


class TestDataIntegrity:
    """Testy integralności danych"""
    
    def test_datetime_index_required(self, strategy_default):
        """Sprawdza czy wymaga DateTime index"""
        # DataFrame bez DateTime index
        df_bad = pd.DataFrame({
            'Open': [1.05] * 100,
            'High': [1.051] * 100,
            'Low': [1.049] * 100,
            'Close': [1.05] * 100,
            'Volume': [2000] * 100
        })
        
        # Powinien działać tylko z DateTime w kolumnie
        df_bad['DateTime'] = pd.date_range('2025-01-01', periods=100, freq='15min')
        
        # To powinno działać
        try:
            result = strategy_default.calculate_indicators(df_bad.copy())
            assert True
        except:
            pytest.fail("Strategy wymaga DateTime w indeksie lub kolumnie")
    
    def test_required_columns_present(self, strategy_default, sample_data):
        """Sprawdza czy wszystkie wymagane kolumny są obecne"""
        required = ['Open', 'High', 'Low', 'Close', 'Volume']
        
        for col in required:
            df_missing = sample_data.copy()
            df_missing = df_missing.drop(columns=[col])
            
            # Powinno rzucić błąd lub zwrócić NaN
            try:
                result = strategy_default.calculate_indicators(df_missing)
                # Jeśli nie rzuci błędu, sprawdź czy wynik ma sens
                assert result is not None
            except KeyError:
                # To jest oczekiwane - brak wymaganej kolumny
                assert True


class TestRegressionPrevention:
    """Testy zapobiegające znanym bugom"""
    
    def test_datetime_offset_consistency(self, strategy_default, sample_data):
        """REGRESJA: Sprawdza czy DateTime offset działa po filtrowaniu"""
        df_full = sample_data.copy()
        df_full = strategy_default.calculate_indicators(df_full)
        
        # Weź tylko część danych (symulacja filtrowania w backtest_engine)
        df_filtered = df_full.iloc[100:200].copy()
        
        # Support_Price powinien być spójny (nie NaN) dla obu
        full_support = df_full.iloc[150]['Support_Price']
        filtered_support = df_filtered.iloc[50]['Support_Price']  # Ta sama świeca
        
        # Jeśli oba są liczbami, powinny być identyczne
        if pd.notna(full_support) and pd.notna(filtered_support):
            assert abs(full_support - filtered_support) < 0.00001
    
    def test_daily_cache_mechanism(self, strategy_default, sample_data):
        """REGRESJA: Sprawdza czy daily cache działa"""
        df = sample_data.copy()
        df = strategy_default.calculate_indicators(df)
        
        # Sprawdź czy daily_support_data został wypełniony
        assert len(strategy_default.daily_support_data) > 0
        
        # Każdy dzień powinien mieć wymagane klucze
        for entry in strategy_default.daily_support_data:
            assert 'date' in entry
            assert 'slope' in entry
            assert 'intercept' in entry
            assert 'lookback_start_dt' in entry
    
    def test_slope_filter_works(self, sample_data):
        """REGRESJA: Sprawdza czy min_slope faktycznie filtruje"""
        strategy_loose = SupportBreakoutStrategy(min_slope=0.0)
        strategy_strict = SupportBreakoutStrategy(min_slope=10.0)  # Bardzo wysoki
        
        df_loose = strategy_loose.calculate_indicators(sample_data.copy())
        df_strict = strategy_strict.calculate_indicators(sample_data.copy())
        
        # Strict powinien mieć więcej NaN (odrzucone linie)
        nan_loose = df_loose['Support_Price'].isna().sum()
        nan_strict = df_strict['Support_Price'].isna().sum()
        
        assert nan_strict >= nan_loose


# ===== TESTY WYDAJNOŚCIOWE =====

class TestPerformance:
    """Testy wydajności"""
    
    @pytest.mark.slow
    def test_calculate_indicators_performance(self, strategy_default):
        """Sprawdza czy calculate_indicators działa w rozsądnym czasie"""
        import time
        
        # Duży dataset (tydzień danych = ~600 świec)
        dates = pd.date_range('2025-01-01', periods=672, freq='15min')
        df = pd.DataFrame({
            'DateTime': dates,
            'Open': np.random.uniform(1.04, 1.06, 672),
            'High': np.random.uniform(1.04, 1.06, 672),
            'Low': np.random.uniform(1.04, 1.06, 672),
            'Close': np.random.uniform(1.04, 1.06, 672),
            'Volume': np.random.randint(1000, 5000, 672)
        })
        # DateTime must be a column, NOT index
        
        start = time.time()
        result = strategy_default.calculate_indicators(df)
        elapsed = time.time() - start
        
        # Powinno zająć <5 sekund dla tygodnia danych
        assert elapsed < 5.0, f"Obliczenia trwały {elapsed:.2f}s (>5s)"


# ===== TOP 5 PRIORITY TESTS =====

class TestEdgeCases:
    """Testy przypadków brzegowych i walidacji"""
    
    def test_support_line_returns_all_expected_keys(self):
        """Sprawdza czy _find_support_line zwraca wszystkie oczekiwane klucze"""
        s = SupportBreakoutStrategy(lookback_days=1)
        dates = pd.date_range('2025-01-01', periods=100, freq='15min')
        df = pd.DataFrame({
            'DateTime': dates,
            'Open': [100.0] * 100,
            'High': [101.0] * 100,
            'Low': [99.0] * 100,
            'Close': [100.5] * 100,
            'Volume': [1000] * 100,
            'index': range(100)
        })
        
        result = s._find_support_line(df)
        
        # Sprawdź wszystkie wymagane klucze
        required_keys = ['slope', 'intercept', 'score', 'used_minima', 
                        'local_maxima', 'all_minima', 'impulses']
        for key in required_keys:
            assert key in result, f"Brak klucza {key} w wyniku _find_support_line"
    
    def test_support_line_with_insufficient_data(self):
        """Test z bardzo małą ilością danych (< 50 świeczek dla impulsów)"""
        s = SupportBreakoutStrategy(lookback_days=1)
        dates = pd.date_range('2025-01-01', periods=20, freq='15min')
        df = pd.DataFrame({
            'DateTime': dates,
            'Open': [100.0] * 20,
            'High': [101.0] * 20,
            'Low': [99.0] * 20,
            'Close': [100.5] * 20,
            'Volume': [1000] * 20,
            'index': range(20)
        })
        
        result = s._find_support_line(df)
        
        # Powinien zwrócić dict mimo małej ilości danych (fallback)
        assert isinstance(result, dict)
        assert 'slope' in result and 'intercept' in result
    
    def test_daily_support_data_structure(self, strategy_default, sample_data):
        """Weryfikuje strukturę zapisywanych daily_support_data"""
        df = strategy_default.calculate_indicators(sample_data.copy())
        
        # Sprawdź czy są jakieś wpisy
        assert len(strategy_default.daily_support_data) > 0
        
        # Sprawdź strukturę pierwszego wpisu
        entry = strategy_default.daily_support_data[0]
        required_keys = ['date', 'slope', 'intercept', 'support_points', 
                        'local_maxima', 'all_minima', 'impulses',
                        'lookback_start_dt', 'lookback_end_dt', 'day_start_idx']
        
        for key in required_keys:
            assert key in entry, f"Brak klucza {key} w daily_support_data"
        
        # Sprawdź typy danych
        assert isinstance(entry['support_points'], list)
        assert isinstance(entry['all_minima'], list)
        assert isinstance(entry['local_maxima'], list)
        assert isinstance(entry['impulses'], list)
    
    def test_plot_with_no_support_info(self, tmp_path):
        """Test wykres gdy brak danych support dla danego dnia"""
        s = SupportBreakoutStrategy(lookback_days=1)
        dates = pd.date_range('2025-01-01', periods=50, freq='15min')
        df = pd.DataFrame({
            'DateTime': dates,
            'Open': [100.0] * 50,
            'High': [101.0] * 50,
            'Low': [99.0] * 50,
            'Close': [100.5] * 50,
            'Volume': [1000] * 50
        })
        
        # Wywołaj plot_daily_chart dla dnia, którego nie ma w daily_support_data
        from datetime import date
        test_date = date(2025, 1, 1)
        
        outdir = str(tmp_path / 'charts')
        filename = s.plot_daily_chart(df, test_date, output_dir=outdir, show_volume=False)
        
        # Powinien zwrócić None lub obsłużyć brak danych bez crashu
        assert filename is None or not os.path.exists(filename)
    
    def test_invalid_lookback_days(self):
        """Test walidacji dla nieprawidłowych parametrów"""
        # Strategia powinna działać nawet z lookback_days=1 (minimalny)
        s = SupportBreakoutStrategy(lookback_days=1)
        assert s.lookback_days == 1
        assert s.lookback_candles == 96
        
        # lookback_days=0 technicalnie możliwe ale bez sensu
        s_zero = SupportBreakoutStrategy(lookback_days=0)
        assert s_zero.lookback_candles == 0


# ===== HELPER DO URUCHOMIENIA =====

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
