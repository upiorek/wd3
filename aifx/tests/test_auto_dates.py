"""
Testy dla automatycznego wykrywania dat (auto dates).
"""

import pytest
import sys
import os
import tempfile
import pandas as pd
from datetime import datetime

# Dodaj parent directory do path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from run_support_backtest import auto_detect_dates


class TestAutoDates:
    """Testy automatycznego wykrywania zakresu dat."""
    
    def test_auto_detect_returns_tuple(self):
        """Test że auto_detect_dates zwraca krotkę (start_date, end_date)."""
        if not os.path.exists('FUS100.15.csv'):
            pytest.skip("Brak pliku FUS100.15.csv")
        
        result = auto_detect_dates('FUS100.15.csv', 'bossa')
        
        assert isinstance(result, tuple)
        assert len(result) == 2
        
        start_date, end_date = result
        assert isinstance(start_date, str)
        assert isinstance(end_date, str)
        
        print(f"✓ Zwraca krotkę: ({start_date}, {end_date})")
    
    def test_auto_detect_date_format(self):
        """Test że daty są w formacie YYYY-MM-DD."""
        if not os.path.exists('FUS100.15.csv'):
            pytest.skip("Brak pliku FUS100.15.csv")
        
        start_date, end_date = auto_detect_dates('FUS100.15.csv', 'bossa')
        
        # Format YYYY-MM-DD
        assert len(start_date) == 10
        assert len(end_date) == 10
        
        # Sprawdź separatory
        assert start_date[4] == '-'
        assert start_date[7] == '-'
        assert end_date[4] == '-'
        assert end_date[7] == '-'
        
        # Sprawdź że można sparsować jako datę
        try:
            datetime.strptime(start_date, '%Y-%m-%d')
            datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            pytest.fail(f"Invalid date format: {start_date} or {end_date}")
        
        print(f"✓ Format YYYY-MM-DD: {start_date}, {end_date}")
    
    def test_auto_detect_chronological_order(self):
        """Test że start_date <= end_date."""
        if not os.path.exists('FUS100.15.csv'):
            pytest.skip("Brak pliku FUS100.15.csv")
        
        start_date, end_date = auto_detect_dates('FUS100.15.csv', 'bossa')
        
        assert start_date <= end_date, f"start_date ({start_date}) > end_date ({end_date})"
        
        print(f"✓ Chronologia OK: {start_date} <= {end_date}")
    
    def test_auto_detect_bossa_format(self):
        """Test auto_detect dla formatu Bossa."""
        if not os.path.exists('FUS100.15.csv'):
            pytest.skip("Brak pliku FUS100.15.csv")
        
        start_date, end_date = auto_detect_dates('FUS100.15.csv', 'bossa')
        
        # Powinny być daty z 2025
        assert start_date.startswith('2025')
        assert end_date.startswith('2025')
        
        print(f"✓ Bossa format: {start_date} to {end_date}")
    
    def test_auto_detect_mbank_format(self):
        """Test auto_detect dla formatu mBank."""
        if not os.path.exists('FUS100.15_single.csv'):
            pytest.skip("Brak pliku FUS100.15_single.csv")
        
        start_date, end_date = auto_detect_dates('FUS100.15_single.csv', 'mbank')
        
        # Powinny być daty z października 2025
        assert start_date.startswith('2025-10')
        assert end_date.startswith('2025-10')
        
        print(f"✓ mBank format: {start_date} to {end_date}")
    
    def test_auto_detect_same_day(self):
        """Test auto_detect dla pliku z danymi z tego samego dnia."""
        # Utwórz tymczasowy plik z danymi z jednego dnia
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', newline='') as f:
            # Format mBank
            f.write("Time;Open;High;Low;Close\n")
            f.write("2025.10.20 09:00;25000.00;25100.00;24900.00;25050.00\n")
            f.write("2025.10.20 09:15;25050.00;25150.00;25000.00;25100.00\n")
            f.write("2025.10.20 09:30;25100.00;25200.00;25050.00;25150.00\n")
            temp_file = f.name
        
        try:
            start_date, end_date = auto_detect_dates(temp_file, 'mbank')
            
            # Dla danych z jednego dnia start_date == end_date
            assert start_date == end_date
            assert start_date == '2025-10-20'
            
            print(f"✓ Same day: {start_date} == {end_date}")
        finally:
            os.unlink(temp_file)
    
    def test_auto_detect_empty_file_raises_error(self):
        """Test że pusty plik zgłasza błąd."""
        # Utwórz pusty plik (tylko nagłówek)
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', newline='') as f:
            f.write("Time;Open;High;Low;Close\n")
            temp_file = f.name
        
        try:
            with pytest.raises(ValueError, match="jest pusty"):
                auto_detect_dates(temp_file, 'mbank')
            
            print("✓ Empty file raises ValueError")
        finally:
            os.unlink(temp_file)
    
    def test_auto_detect_multiple_months(self):
        """Test auto_detect dla danych obejmujących wiele miesięcy."""
        # Utwórz plik z danymi z wielu miesięcy
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', newline='') as f:
            f.write("Time;Open;High;Low;Close\n")
            f.write("2025.09.15 09:00;25000.00;25100.00;24900.00;25050.00\n")
            f.write("2025.10.20 09:00;25200.00;25300.00;25100.00;25250.00\n")
            f.write("2025.11.10 09:00;25400.00;25500.00;25300.00;25450.00\n")
            temp_file = f.name
        
        try:
            start_date, end_date = auto_detect_dates(temp_file, 'mbank')
            
            assert start_date == '2025-09-15'
            assert end_date == '2025-11-10'
            
            # Sprawdź że różnica to ~2 miesiące
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            days_diff = (end_dt - start_dt).days
            assert days_diff > 30  # Ponad miesiąc
            
            print(f"✓ Multiple months: {start_date} to {end_date} ({days_diff} days)")
        finally:
            os.unlink(temp_file)


if __name__ == '__main__':
    # Uruchom testy
    sys.exit(pytest.main([__file__, '-v']))
