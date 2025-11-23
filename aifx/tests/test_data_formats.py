"""
Testy dla różnych formatów danych (Bossa vs mBank).
"""

import pandas as pd
import pytest
import sys
import os

# Dodaj parent directory do path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from run_support_backtest import load_data, auto_detect_dates


class TestDataFormats:
    """Testy wczytywania różnych formatów danych."""
    
    def test_load_bossa_format(self):
        """Test wczytywania formatu Bossa (tab-separated z <DATE>, <TIME>)."""
        # Ten test wymaga pliku FUS100.15.csv
        if not os.path.exists('FUS100.15.csv'):
            pytest.skip("Brak pliku FUS100.15.csv")
        
        df = load_data('FUS100.15.csv', data_format='bossa')
        
        # Sprawdź że DataFrame ma wymagane kolumny
        assert 'DateTime' in df.columns
        assert 'Open' in df.columns
        assert 'High' in df.columns
        assert 'Low' in df.columns
        assert 'Close' in df.columns
        assert 'Volume' in df.columns
        
        # Sprawdź że dane są wczytane
        assert len(df) > 0
        
        # Sprawdź typy
        assert pd.api.types.is_datetime64_any_dtype(df['DateTime'])
        assert pd.api.types.is_numeric_dtype(df['Open'])
        assert pd.api.types.is_numeric_dtype(df['High'])
        assert pd.api.types.is_numeric_dtype(df['Low'])
        assert pd.api.types.is_numeric_dtype(df['Close'])
        
        print(f"✓ Format Bossa: {len(df)} świeczek")
    
    def test_load_mbank_format(self):
        """Test wczytywania formatu mBank (semicolon-separated z Time)."""
        # Ten test wymaga pliku FUS100.15_single.csv
        if not os.path.exists('FUS100.15_single.csv'):
            pytest.skip("Brak pliku FUS100.15_single.csv")
        
        df = load_data('FUS100.15_single.csv', data_format='mbank')
        
        # Sprawdź że DataFrame ma wymagane kolumny
        assert 'DateTime' in df.columns
        assert 'Open' in df.columns
        assert 'High' in df.columns
        assert 'Low' in df.columns
        assert 'Close' in df.columns
        assert 'Volume' in df.columns
        
        # Sprawdź że dane są wczytane
        assert len(df) > 0
        
        # Sprawdź typy
        assert pd.api.types.is_datetime64_any_dtype(df['DateTime'])
        assert pd.api.types.is_numeric_dtype(df['Open'])
        assert pd.api.types.is_numeric_dtype(df['High'])
        assert pd.api.types.is_numeric_dtype(df['Low'])
        assert pd.api.types.is_numeric_dtype(df['Close'])
        
        # Volume powinno być 0 dla formatu mBank (brak danych volume)
        assert (df['Volume'] == 0).all()
        
        print(f"✓ Format mBank: {len(df)} świeczek")
    
    def test_mbank_datetime_parsing(self):
        """Test parsowania DateTime w formacie mBank (YYYY.MM.DD HH:MM)."""
        if not os.path.exists('FUS100.15_single.csv'):
            pytest.skip("Brak pliku FUS100.15_single.csv")
        
        df = load_data('FUS100.15_single.csv', data_format='mbank')
        
        # Sprawdź że DateTime jest poprawnie sparsowany
        first_dt = df['DateTime'].iloc[0]
        
        # Powinien być obiekt datetime
        assert isinstance(first_dt, pd.Timestamp)
        
        # Sprawdź zakres dat (powinny być z października/listopada 2025)
        assert first_dt.year == 2025
        assert first_dt.month in [10, 11]
        
        print(f"✓ DateTime parsing: {first_dt}")
    
    def test_data_consistency(self):
        """Test spójności danych: High >= Low, High >= Open/Close, Low <= Open/Close."""
        if not os.path.exists('FUS100.15_single.csv'):
            pytest.skip("Brak pliku FUS100.15_single.csv")
        
        df = load_data('FUS100.15_single.csv', data_format='mbank')
        
        # High >= Low zawsze
        assert (df['High'] >= df['Low']).all(), "High powinno być >= Low"
        
        # High >= Open i Close
        assert (df['High'] >= df['Open']).all(), "High powinno być >= Open"
        assert (df['High'] >= df['Close']).all(), "High powinno być >= Close"
        
        # Low <= Open i Close
        assert (df['Low'] <= df['Open']).all(), "Low powinno być <= Open"
        assert (df['Low'] <= df['Close']).all(), "Low powinno być <= Close"
        
        print("✓ Spójność danych OK")
    
    def test_default_format_is_bossa(self):
        """Test że domyślny format to 'bossa'."""
        if not os.path.exists('FUS100.15.csv'):
            pytest.skip("Brak pliku FUS100.15.csv")
        
        # Bez podania data_format powinien użyć 'bossa'
        df1 = load_data('FUS100.15.csv')
        df2 = load_data('FUS100.15.csv', data_format='bossa')
        
        # Powinny być identyczne
        assert len(df1) == len(df2)
        assert list(df1.columns) == list(df2.columns)
        
        print("✓ Domyślny format: bossa")
    
    def test_auto_detect_dates_bossa(self):
        """Test automatycznego wykrywania dat dla formatu Bossa."""
        if not os.path.exists('FUS100.15.csv'):
            pytest.skip("Brak pliku FUS100.15.csv")
        
        start_date, end_date = auto_detect_dates('FUS100.15.csv', data_format='bossa')
        
        # Sprawdź format dat (YYYY-MM-DD)
        assert len(start_date) == 10
        assert len(end_date) == 10
        assert start_date[4] == '-' and start_date[7] == '-'
        assert end_date[4] == '-' and end_date[7] == '-'
        
        # start_date <= end_date
        assert start_date <= end_date
        
        print(f"✓ Auto-detect Bossa: {start_date} to {end_date}")
    
    def test_auto_detect_dates_mbank(self):
        """Test automatycznego wykrywania dat dla formatu mBank."""
        if not os.path.exists('FUS100.15_single.csv'):
            pytest.skip("Brak pliku FUS100.15_single.csv")
        
        start_date, end_date = auto_detect_dates('FUS100.15_single.csv', data_format='mbank')
        
        # Sprawdź format dat (YYYY-MM-DD)
        assert len(start_date) == 10
        assert len(end_date) == 10
        assert start_date[4] == '-' and start_date[7] == '-'
        assert end_date[4] == '-' and end_date[7] == '-'
        
        # start_date <= end_date
        assert start_date <= end_date
        
        # Powinny być z października 2025
        assert start_date.startswith('2025-10')
        
        print(f"✓ Auto-detect mBank: {start_date} to {end_date}")


if __name__ == '__main__':
    # Uruchom testy
    import sys
    sys.exit(pytest.main([__file__, '-v']))
