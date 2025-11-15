"""
Simple test for analyze_candles.py
"""

import os
import tempfile
import csv
from datetime import datetime
from analyze_candles import analyze_candles


def verify_log_file(temp_filename, expected_white, expected_black, expected_decision):
    """Verify that the log file was created with correct content"""
    log_filename = f"analysis_{datetime.now().strftime('%Y-%m-%d')}.log"
    
    assert os.path.exists(log_filename), f"Log file {log_filename} was not created"
    
    # Read the last line of the log file
    with open(log_filename, 'r') as f:
        lines = f.readlines()
        assert len(lines) > 0, "Log file is empty"
        last_line = lines[-1]
    
    # Verify log content
    assert os.path.basename(temp_filename) in last_line, f"Filename not found in log"
    assert f"White:{expected_white}" in last_line, f"Expected White:{expected_white} in log"
    assert f"Black:{expected_black}" in last_line, f"Expected Black:{expected_black} in log"
    assert f"Decision:{expected_decision}" in last_line, f"Expected Decision:{expected_decision} in log"
    
    return True


def test_more_white_candles():
    """Test with more white (bullish) candles"""
    # Create temporary CSV file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(['Time', 'Open', 'High', 'Low', 'Close', 'Volume'])
        # 3 white candles (close > open)
        writer.writerow(['2025.11.12 10:00', '100.0', '105.0', '99.0', '104.0', '1000'])
        writer.writerow(['2025.11.12 10:15', '104.0', '110.0', '103.0', '108.0', '1000'])
        writer.writerow(['2025.11.12 10:30', '108.0', '112.0', '107.0', '111.0', '1000'])
        # 1 black candle (close < open)
        writer.writerow(['2025.11.12 10:45', '111.0', '112.0', '106.0', '107.0', '1000'])
        temp_file = f.name
    
    try:
        result = analyze_candles(temp_file)
        assert result == True, "Should return True when more white candles"
        verify_log_file(temp_file, 3, 1, "BUY")
        print("✓ Test passed: More white candles (including log validation)")
    finally:
        os.unlink(temp_file)


def test_more_black_candles():
    """Test with more black (bearish) candles"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(['Time', 'Open', 'High', 'Low', 'Close', 'Volume'])
        # 1 white candle
        writer.writerow(['2025.11.12 10:00', '100.0', '105.0', '99.0', '104.0', '1000'])
        # 3 black candles (close < open)
        writer.writerow(['2025.11.12 10:15', '104.0', '105.0', '98.0', '99.0', '1000'])
        writer.writerow(['2025.11.12 10:30', '99.0', '100.0', '94.0', '95.0', '1000'])
        writer.writerow(['2025.11.12 10:45', '95.0', '96.0', '90.0', '91.0', '1000'])
        temp_file = f.name
    
    try:
        result = analyze_candles(temp_file)
        assert result == False, "Should return False when more black candles"
        verify_log_file(temp_file, 1, 3, "SELL")
        print("✓ Test passed: More black candles (including log validation)")
    finally:
        os.unlink(temp_file)


def test_equal_candles():
    """Test with equal white and black candles"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(['Time', 'Open', 'High', 'Low', 'Close', 'Volume'])
        # 2 white candles
        writer.writerow(['2025.11.12 10:00', '100.0', '105.0', '99.0', '104.0', '1000'])
        writer.writerow(['2025.11.12 10:15', '104.0', '110.0', '103.0', '108.0', '1000'])
        # 2 black candles
        writer.writerow(['2025.11.12 10:30', '108.0', '109.0', '102.0', '103.0', '1000'])
        writer.writerow(['2025.11.12 10:45', '103.0', '104.0', '98.0', '99.0', '1000'])
        temp_file = f.name
    
    try:
        result = analyze_candles(temp_file)
        assert result == False, "Should return False when equal (not more white)"
        verify_log_file(temp_file, 2, 2, "SELL")
        print("✓ Test passed: Equal candles (including log validation)")
    finally:
        os.unlink(temp_file)


def test_with_doji():
    """Test with doji candles (close == open)"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(['Time', 'Open', 'High', 'Low', 'Close', 'Volume'])
        # 2 white candles
        writer.writerow(['2025.11.12 10:00', '100.0', '105.0', '99.0', '104.0', '1000'])
        writer.writerow(['2025.11.12 10:15', '104.0', '110.0', '103.0', '108.0', '1000'])
        # 1 black candle
        writer.writerow(['2025.11.12 10:30', '108.0', '109.0', '102.0', '103.0', '1000'])
        # 1 doji (should be ignored)
        writer.writerow(['2025.11.12 10:45', '103.0', '105.0', '101.0', '103.0', '1000'])
        temp_file = f.name
    
    try:
        result = analyze_candles(temp_file)
        assert result == True, "Should return True (2 white > 1 black, doji ignored)"
        verify_log_file(temp_file, 2, 1, "BUY")
        print("✓ Test passed: With doji candles (including log validation)")
    finally:
        os.unlink(temp_file)


if __name__ == "__main__":
    print("Running tests for analyze_candles.py...")
    print()
    
    try:
        test_more_white_candles()
        test_more_black_candles()
        test_equal_candles()
        test_with_doji()
        
        print()
        print("=" * 50)
        print("✓ ALL TESTS PASSED")
        print("=" * 50)
        
    except AssertionError as e:
        print()
        print("=" * 50)
        print(f"✗ TEST FAILED: {e}")
        print("=" * 50)
        exit(1)
    except Exception as e:
        print()
        print("=" * 50)
        print(f"✗ ERROR: {e}")
        print("=" * 50)
        exit(1)
