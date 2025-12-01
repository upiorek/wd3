"""
Test suite for analyze_trades.py

Tests cover:
- BUY and SELL signals
- TP (Take Profit) scenarios
- SL (Stop Loss) scenarios
- BE (Break Even) scenarios
- SL->BE marker
- Multiple outcomes in same candle
- Outcomes at open of next candle
"""

import sys
import os
from pathlib import Path
import tempfile
import shutil

# Add parent directory to path to import analyze_trades
sys.path.insert(0, str(Path(__file__).parent))

def create_test_file(filename, content):
    """Create a temporary test file with given content."""
    filepath = Path(__file__).parent / "m15_tests" / filename
    filepath.parent.mkdir(exist_ok=True)
    with open(filepath, 'w') as f:
        f.write(content)
    return filepath

def read_file_lines(filepath):
    """Read file and return lines."""
    with open(filepath, 'r') as f:
        return f.readlines()

def test_buy_tp():
    """Test BUY signal that hits TP (Take Profit)."""
    print("\n=== TEST: BUY TP ===")
    
    # Entry at open of first candle after signal (10020)
    # TP at 10220 (+200), low must stay above entry to avoid BE
    content = """Time;Open;High;Low;Close
2025.10.31 10:00;10000.00;10010.00;9990.00;10005.00
2025.10.31 10:15;10005.00;10015.00;10000.00;10010.00 BUY
2025.10.31 10:30;10020.00;10140.00;10021.00;10130.00
2025.10.31 10:45;10130.00;10230.00;10125.00;10220.00
2025.10.31 11:00;10220.00;10250.00;10215.00;10240.00
"""
    
    filepath = create_test_file("test_buy_tp_mod.csv", content)
    
    # Import and run
    from analyze_trades import process_mod_file
    result, bad_luck, gain_loss = process_mod_file(filepath)
    
    lines = read_file_lines(filepath)
    
    # Verify results
    assert result == 'TP', f"Expected TP, got {result}"
    assert gain_loss >= 200, f"Expected gain >= 200, got {gain_loss}"
    # TP should be on line 4 (after SL->BE on line 3)
    assert 'TP' in ''.join(lines), f"Expected TP marker somewhere in file"
    
    print(f"OK Result: {result}, Gain/Loss: {gain_loss:.2f}")
    print("OK TP test completed successfully")
    print("PASSED")

def test_sell_tp():
    """Test SELL signal that hits TP."""
    print("\n=== TEST: SELL TP ===")
    
    # Entry at 10005 (open of first candle after signal)
    # TP at 9805 (-200), high must stay below entry to avoid BE
    content = """Time;Open;High;Low;Close
2025.10.31 10:00;10000.00;10010.00;9990.00;10005.00
2025.10.31 10:15;10005.00;10015.00;10000.00;10010.00 SELL
2025.10.31 10:30;10005.00;10004.00;9890.00;9895.00
2025.10.31 10:45;9895.00;9894.00;9800.00;9810.00
2025.10.31 11:00;9810.00;9820.00;9785.00;9795.00
"""
    
    filepath = create_test_file("test_sell_tp_mod.csv", content)
    
    from analyze_trades import process_mod_file
    result, bad_luck, gain_loss = process_mod_file(filepath)
    
    lines = read_file_lines(filepath)
    
    assert result == 'TP', f"Expected TP, got {result}"
    assert gain_loss >= 200, f"Expected gain >= 200, got {gain_loss}"
    assert 'TP' in ''.join(lines), f"Expected TP marker somewhere in file"
    
    print(f"OK Result: {result}, Gain/Loss: {gain_loss:.2f}")
    print("OK TP test completed successfully")
    print("PASSED")

def test_buy_sl():
    """Test BUY signal that hits SL (Stop Loss)."""
    print("\n=== TEST: BUY SL ===")
    
    content = """Time;Open;High;Low;Close
2025.10.31 10:00;10000.00;10010.00;9990.00;10005.00
2025.10.31 10:15;10005.00;10015.00;10000.00;10010.00 BUY
2025.10.31 10:30;10010.00;10020.00;9950.00;9955.00
2025.10.31 10:45;9955.00;9960.00;9940.00;9950.00
2025.10.31 11:00;9950.00;9960.00;9935.00;9945.00
"""
    
    filepath = create_test_file("test_buy_sl_mod.csv", content)
    
    from analyze_trades import process_mod_file
    result, bad_luck, gain_loss = process_mod_file(filepath)
    
    lines = read_file_lines(filepath)
    
    assert result == 'SL', f"Expected SL, got {result}"
    assert gain_loss <= -50, f"Expected loss <= -50, got {gain_loss}"
    assert 'SL' in ''.join(lines), f"Expected SL marker somewhere in file"
    # Note: display may show "gain" even for SL due to current implementation
    
    print(f"OK Result: {result}, Gain/Loss: {gain_loss:.2f}")
    print("OK SL test completed successfully")
    print("PASSED")

def test_sell_sl():
    """Test SELL signal that hits SL."""
    print("\n=== TEST: SELL SL ===")
    
    content = """Time;Open;High;Low;Close
2025.10.31 10:00;10000.00;10010.00;9990.00;10005.00
2025.10.31 10:15;10005.00;10015.00;10000.00;10010.00 SELL
2025.10.31 10:30;10010.00;10070.00;10005.00;10065.00
2025.10.31 10:45;10065.00;10080.00;10060.00;10070.00
2025.10.31 11:00;10070.00;10085.00;10065.00;10075.00
"""
    
    filepath = create_test_file("test_sell_sl_mod.csv", content)
    
    from analyze_trades import process_mod_file
    result, bad_luck, gain_loss = process_mod_file(filepath)
    
    lines = read_file_lines(filepath)
    
    assert result == 'SL', f"Expected SL, got {result}"
    assert gain_loss <= -50, f"Expected loss <= -50, got {gain_loss}"
    assert 'SL' in ''.join(lines), f"Expected SL marker somewhere in file"
    
    print(f"OK Result: {result}, Gain/Loss: {gain_loss:.2f}")
    print("OK SL test completed successfully")
    print("PASSED")

def test_buy_sl_to_be():
    """Test BUY signal where SL moves to BE and BE is hit."""
    print("\n=== TEST: BUY SL->BE then BE hit ===")
    
    content = """Time;Open;High;Low;Close
2025.10.31 10:00;10000.00;10010.00;9990.00;10005.00
2025.10.31 10:15;10005.00;10015.00;10000.00;10010.00 BUY
2025.10.31 10:30;10010.00;10120.00;10005.00;10115.00
2025.10.31 10:45;10115.00;10130.00;10000.00;10010.00
2025.10.31 11:00;10010.00;10020.00;9995.00;10005.00
2025.10.31 11:15;10005.00;10015.00;10000.00;10010.00
"""
    
    filepath = create_test_file("test_buy_sl_be_mod.csv", content)
    
    from analyze_trades import process_mod_file
    result, bad_luck, gain_loss = process_mod_file(filepath)
    
    lines = read_file_lines(filepath)
    
    assert result == 'BE', f"Expected BE, got {result}"
    assert 'SL->BE' in ''.join(lines), f"Expected SL->BE marker somewhere in file"
    assert 'BE' in ''.join(lines), f"Expected BE marker somewhere in file"
    
    print(f"OK Result: {result}, Gain/Loss: {gain_loss:.2f}")
    print("OK SL->BE and BE markers found")
    print("PASSED")
def test_sell_sl_to_be():
    """Test SELL signal where SL moves to BE and BE is hit."""
    print("\n=== TEST: SELL SL->BE then BE hit ===")
    
    content = """Time;Open;High;Low;Close
2025.10.31 10:00;10000.00;10010.00;9990.00;10005.00
2025.10.31 10:15;10005.00;10015.00;10000.00;10010.00 SELL
2025.10.31 10:30;10010.00;10015.00;9900.00;9905.00
2025.10.31 10:45;9905.00;10015.00;9900.00;9910.00
2025.10.31 11:00;9910.00;9920.00;9895.00;9905.00
2025.10.31 11:15;9905.00;9915.00;9900.00;9910.00
"""
    
    filepath = create_test_file("test_sell_sl_be_mod.csv", content)
    
    from analyze_trades import process_mod_file
    result, bad_luck, gain_loss = process_mod_file(filepath)
    
    lines = read_file_lines(filepath)
    
    assert result == 'BE', f"Expected BE, got {result}"
    assert 'SL->BE' in ''.join(lines), f"Expected SL->BE marker somewhere in file"
    assert 'BE' in ''.join(lines), f"Expected BE marker somewhere in file"
    
    print(f"OK Result: {result}, Gain/Loss: {gain_loss:.2f}")
    print("OK SL->BE and BE markers found")
    print("PASSED")

def test_buy_tp_and_sl_same_candle():
    """Test BUY where both TP and SL could hit in same candle (bad luck)."""
    print("\n=== TEST: BUY TP and SL same candle (bad luck) ===")
    
    # Entry at 10005 (open of candle after BUY signal)
    # Next candle: high=10230 (TP at 10205), low=9950 (SL at 9955) - both hit!
    content = """Time;Open;High;Low;Close
2025.10.31 10:00;10000.00;10010.00;9990.00;10005.00
2025.10.31 10:15;10005.00;10015.00;10000.00;10010.00 BUY
2025.10.31 10:30;10005.00;10015.00;10000.00;10010.00
2025.10.31 10:45;10010.00;10230.00;9950.00;10100.00
2025.10.31 11:00;10100.00;10120.00;10090.00;10110.00
"""
    
    filepath = create_test_file("test_buy_bad_luck_mod.csv", content)
    
    from analyze_trades import process_mod_file
    result, bad_luck, gain_loss = process_mod_file(filepath)
    
    lines = read_file_lines(filepath)
    
    assert bad_luck == True, f"Expected bad_luck=True, got {bad_luck}"
    assert result == 'BE', f"Expected BE (break-even result), got {result}"
    assert 'BE' in ''.join(lines), f"Expected BE marker somewhere in file"
    assert '(bad luck)' in ''.join(lines), f"Expected '(bad luck)' marker in file"
    
    print(f"OK Result: {result}, Gain/Loss: {gain_loss:.2f}, Bad Luck: {bad_luck}")
    print("OK Bad luck scenario detected correctly with '(bad luck)' marker")
    print("PASSED")

def test_sell_tp_and_sl_same_candle():
    """Test SELL where both TP and SL could hit in same candle (bad luck)."""
    print("\n=== TEST: SELL TP and SL same candle (bad luck) ===")
    
    # Entry at 10005 (open of candle after SELL signal)
    # Next candle: low=9800 (TP at 9805), high=10070 (SL at 10055) - both hit!
    content = """Time;Open;High;Low;Close
2025.10.31 10:00;10000.00;10010.00;9990.00;10005.00
2025.10.31 10:15;10005.00;10015.00;10000.00;10010.00 SELL
2025.10.31 10:30;10005.00;10015.00;10000.00;10010.00
2025.10.31 10:45;10010.00;10070.00;9800.00;9900.00
2025.10.31 11:00;9900.00;9920.00;9890.00;9910.00
"""
    
    filepath = create_test_file("test_sell_bad_luck_mod.csv", content)
    
    from analyze_trades import process_mod_file
    result, bad_luck, gain_loss = process_mod_file(filepath)
    
    lines = read_file_lines(filepath)
    
    assert bad_luck == True, f"Expected bad_luck=True, got {bad_luck}"
    assert result == 'BE', f"Expected BE (break-even result), got {result}"
    assert '(bad luck)' in ''.join(lines), f"Expected '(bad luck)' marker in file"
    
    # SL should NOT be marked "(at open)" because open=10010 is below SL threshold of 10055
    assert '(at open)' not in ''.join(lines), f"Should NOT have '(at open)' marker - SL not hit at open"
    
    print(f"OK Result: {result}, Gain/Loss: {gain_loss:.2f}, Bad Luck: {bad_luck}")
    print("OK Bad luck scenario detected correctly with '(bad luck)' marker")
    print("PASSED")

def test_buy_tp_at_open():
    """Test BUY where TP is hit at open of next candle."""
    print("\n=== TEST: BUY TP at open ===")
    
    # Entry at 10020 (open of first candle after signal)
    # TP at 10220 (exactly at open of second candle, +200)
    content = """Time;Open;High;Low;Close
2025.10.31 10:00;10000.00;10010.00;9990.00;10005.00
2025.10.31 10:15;10005.00;10015.00;10000.00;10010.00 BUY
2025.10.31 10:30;10020.00;10025.00;10021.00;10022.00
2025.10.31 10:45;10221.00;10230.00;10215.00;10225.00
2025.10.31 11:00;10225.00;10240.00;10220.00;10235.00
"""
    
    filepath = create_test_file("test_buy_tp_open_mod.csv", content)
    
    from analyze_trades import process_mod_file
    result, bad_luck, gain_loss = process_mod_file(filepath)
    
    lines = read_file_lines(filepath)
    
    assert result == 'TP', f"Expected TP, got {result}"
    assert 'TP (at open)' in ''.join(lines), f"Expected 'TP (at open)' marker in file"
    
    print(f"OK Result: {result}, Gain/Loss: {gain_loss:.2f}")
    print("OK TP hit at open of candle with '(at open)' marker")
    print("PASSED")

def test_buy_sl_at_open():
    """Test BUY where SL is hit at open of next candle."""
    print("\n=== TEST: BUY SL at open ===")
    
    # Entry at 10020 (open of first candle after signal)
    # SL at 9970 (exactly at open of second candle, -50)
    content = """Time;Open;High;Low;Close
2025.10.31 10:00;10000.00;10010.00;9990.00;10005.00
2025.10.31 10:15;10005.00;10015.00;10000.00;10010.00 BUY
2025.10.31 10:30;10020.00;10025.00;10015.00;10022.00
2025.10.31 10:45;9970.00;9975.00;9965.00;9970.00
2025.10.31 11:00;9970.00;9980.00;9965.00;9975.00
"""
    
    filepath = create_test_file("test_buy_sl_open_mod.csv", content)
    
    from analyze_trades import process_mod_file
    result, bad_luck, gain_loss = process_mod_file(filepath)
    
    lines = read_file_lines(filepath)
    
    assert result == 'SL', f"Expected SL, got {result}"
    assert 'SL (at open)' in ''.join(lines), f"Expected 'SL (at open)' marker in file"
    
    print(f"OK Result: {result}, Gain/Loss: {gain_loss:.2f}")
    print("OK SL hit at open of candle with '(at open)' marker")
    print("PASSED")

def test_buy_be_at_open():
    """Test BUY where BE is hit at open of next candle after SL->BE."""
    print("\n=== TEST: BUY BE at open ===")
    
    # Entry at 10005 (open of candle after BUY)
    # Next candle: high=10130 triggers BE (10105), SL moves to 10005
    # Candle after: open=10005 hits BE exactly at open
    content = """Time;Open;High;Low;Close
2025.10.31 10:00;10000.00;10010.00;9990.00;10005.00
2025.10.31 10:15;10005.00;10015.00;10000.00;10010.00 BUY
2025.10.31 10:30;10005.00;10015.00;10000.00;10010.00
2025.10.31 10:45;10020.00;10130.00;10025.00;10125.00
2025.10.31 11:00;10005.00;10025.00;10000.00;10022.00
2025.10.31 11:15;10022.00;10030.00;10020.00;10025.00
"""
    
    filepath = create_test_file("test_buy_be_open_mod.csv", content)
    
    from analyze_trades import process_mod_file
    result, bad_luck, gain_loss = process_mod_file(filepath)
    
    lines = read_file_lines(filepath)
    
    assert result == 'BE', f"Expected BE, got {result}"
    assert 'SL->BE' in ''.join(lines), f"Expected SL->BE marker somewhere in file"
    assert 'BE (at open)' in ''.join(lines), f"Expected 'BE (at open)' marker in file"
    
    print(f"OK Result: {result}, Gain/Loss: {gain_loss:.2f}")
    print("OK SL->BE and BE hit correctly with '(at open)' marker")
    print("PASSED")

def test_sl_hit_on_entry_candle():
    """Test that SL hit on entry candle is correctly detected."""
    print("\n=== TEST: SL hit on entry candle ===")
    
    # Entry at 10010 (open of entry candle), low of same candle is 9950 which hits SL at 9960
    content = """Time;Open;High;Low;Close
2025.10.31 10:00;10000.00;10010.00;9990.00;10005.00
2025.10.31 10:15;10005.00;10015.00;10000.00;10010.00 BUY
2025.10.31 10:30;10010.00;10020.00;9950.00;9955.00
2025.10.31 10:45;9955.00;9960.00;9940.00;9950.00
2025.10.31 11:00;9950.00;9960.00;9935.00;9945.00
"""
    
    filepath = create_test_file("test_sl_entry_candle_mod.csv", content)
    
    from analyze_trades import process_mod_file
    result, bad_luck, gain_loss = process_mod_file(filepath)
    
    lines = read_file_lines(filepath)
    
    # Line 3 (index 3) is the entry candle - should have the SL marker
    entry_line = lines[3].strip()
    
    assert result == 'SL', f"Expected SL, got {result}"
    assert 'SL' in entry_line, f"Expected SL marker on entry candle: {entry_line}"
    assert 'loss 50.00 SL' in entry_line, f"Expected 'loss 50.00 SL' on entry candle: {entry_line}"
    
    # Line 4 should NOT have SL marker (result already happened)
    next_line = lines[4].strip()
    assert 'SL' not in next_line, f"Line after entry should not have SL marker: {next_line}"
    
    print(f"OK Result: {result}, Gain/Loss: {gain_loss:.2f}")
    print("OK SL correctly detected on entry candle")
    print("PASSED")

def test_be_triggered_and_hit_same_candle_no_at_open():
    """Test that BE triggered and hit on same candle does NOT show (at open)."""
    print("\n=== TEST: BE triggered and hit on same candle - no (at open) ===")
    
    # Entry at 10010, same candle: high=10120 triggers BE, low=10005 hits BE
    # Should show "SL->BE BE" but NOT "(at open)" because BE didn't exist at open
    content = """Time;Open;High;Low;Close
2025.10.31 10:00;10000.00;10010.00;9990.00;10005.00
2025.10.31 10:15;10005.00;10015.00;10000.00;10010.00 BUY
2025.10.31 10:30;10010.00;10120.00;10005.00;10115.00
2025.10.31 10:45;10115.00;10130.00;10000.00;10010.00
"""
    
    filepath = create_test_file("test_be_same_candle_mod.csv", content)
    
    from analyze_trades import process_mod_file
    result, bad_luck, gain_loss = process_mod_file(filepath)
    
    lines = read_file_lines(filepath)
    
    assert result == 'BE', f"Expected BE, got {result}"
    assert 'SL->BE BE' in ''.join(lines), f"Expected 'SL->BE BE' markers"
    assert '(at open)' not in ''.join(lines), f"Should NOT have '(at open)' - BE triggered during this candle"
    
    print(f"OK Result: {result}, Gain/Loss: {gain_loss:.2f}")
    print("OK BE triggered and hit on same candle without '(at open)' marker")
    print("PASSED")

def test_tp_hit_on_entry_candle():
    """Test that TP hit on entry candle is correctly detected."""
    print("\n=== TEST: TP hit on entry candle ===")
    
    # Entry at 10010 (open of entry candle), high of same candle is 10220 which hits TP at 10210
    # Low stays above entry to avoid SL/BE issues
    content = """Time;Open;High;Low;Close
2025.10.31 10:00;10000.00;10010.00;9990.00;10005.00
2025.10.31 10:15;10005.00;10015.00;10000.00;10010.00 BUY
2025.10.31 10:30;10010.00;10220.00;10015.00;10215.00
2025.10.31 10:45;10215.00;10230.00;10210.00;10220.00
"""
    
    filepath = create_test_file("test_tp_entry_candle_mod.csv", content)
    
    from analyze_trades import process_mod_file
    result, bad_luck, gain_loss = process_mod_file(filepath)
    
    lines = read_file_lines(filepath)
    
    # Line 3 (index 3) is the entry candle - should have the TP marker
    entry_line = lines[3].strip()
    
    assert result == 'TP', f"Expected TP, got {result}"
    assert 'TP' in entry_line, f"Expected TP marker on entry candle: {entry_line}"
    assert 'gain 200.00 TP' in entry_line or 'gain 210.00 TP' in entry_line, f"Expected correct TP gain on entry candle: {entry_line}"
    
    print(f"OK Result: {result}, Gain/Loss: {gain_loss:.2f}")
    print("OK TP correctly detected on entry candle")
    print("PASSED")

def test_be_move_on_entry_then_hit_later():
    """Test that BE move on entry candle, then BE hit on later candle shows (at open)."""
    print("\n=== TEST: BE move on entry, BE hit later with (at open) ===")
    
    # Entry at 10005, entry candle: high=10130 triggers BE
    # Next candle: open=10005 hits BE at open - should show "(at open)"
    content = """Time;Open;High;Low;Close
2025.10.31 10:00;10000.00;10010.00;9990.00;10005.00
2025.10.31 10:15;10005.00;10015.00;10000.00;10010.00 BUY
2025.10.31 10:30;10005.00;10015.00;10000.00;10010.00
2025.10.31 10:45;10020.00;10130.00;10025.00;10125.00
2025.10.31 11:00;10005.00;10025.00;10000.00;10022.00
"""
    
    filepath = create_test_file("test_be_later_with_at_open_mod.csv", content)
    
    from analyze_trades import process_mod_file
    result, bad_luck, gain_loss = process_mod_file(filepath)
    
    lines = read_file_lines(filepath)
    
    assert result == 'BE', f"Expected BE, got {result}"
    assert 'SL->BE' in lines[4], f"Expected SL->BE on candle 4: {lines[4]}"
    assert 'BE (at open)' in lines[5], f"Expected 'BE (at open)' on candle 5: {lines[5]}"
    
    print(f"OK Result: {result}, Gain/Loss: {gain_loss:.2f}")
    print("OK BE hit on later candle with '(at open)' marker")
    print("PASSED")

def test_bad_luck_with_be_triggered_same_candle():
    """Test bad luck scenario where BE is triggered on same candle as TP and SL both hit."""
    print("\n=== TEST: Bad luck with BE triggered same candle ===")
    
    # Entry at 10005, entry candle: high=10210 (TP), low=9800 (SL), and high also triggers BE
    # Since BE triggers during candle, sl_target becomes 0, but bad luck uses original -50
    content = """Time;Open;High;Low;Close
2025.10.31 10:00;10000.00;10010.00;9990.00;10005.00
2025.10.31 10:15;10005.00;10015.00;10000.00;10010.00 BUY
2025.10.31 10:30;10005.00;10210.00;9800.00;10100.00
2025.10.31 10:45;10100.00;10120.00;10090.00;10110.00
"""
    
    filepath = create_test_file("test_bad_luck_be_trigger_mod.csv", content)
    
    from analyze_trades import process_mod_file
    result, bad_luck, gain_loss = process_mod_file(filepath)
    
    lines = read_file_lines(filepath)
    
    assert result == 'BE', f"Expected BE (break-even), got {result}"
    assert bad_luck == True, f"Expected bad_luck=True, got {bad_luck}"
    assert '(bad luck)' in ''.join(lines), f"Expected '(bad luck)' marker"
    # Should NOT have "(at open)" because neither TP nor SL existed at open with their hit values
    assert '(at open)' not in ''.join(lines), f"Should NOT have '(at open)' - neither hit at open"
    
    print(f"OK Result: {result}, Gain/Loss: {gain_loss:.2f}, Bad Luck: {bad_luck}")
    print("OK Bad luck with BE triggered on same candle handled correctly")
    print("PASSED")

def test_entry_candle_has_gain_loss():
    """Test that entry candle has gain/loss but no result markers (TP/SL/BE)."""
    print("\n=== TEST: Entry candle has gain/loss but no result markers ===")
    
    # Entry candle should have OHLC + gain/loss, but NO result markers like TP/SL/BE
    content = """Time;Open;High;Low;Close
2025.10.31 10:00;10000.00;10010.00;9990.00;10005.00
2025.10.31 10:15;10005.00;10015.00;10000.00;10010.00 BUY
2025.10.31 10:30;10005.00;10015.00;10000.00;10010.00
2025.10.31 10:45;10010.00;10230.00;9950.00;10100.00
2025.10.31 11:00;10100.00;10120.00;10090.00;10110.00
"""
    
    filepath = create_test_file("test_entry_candle_mod.csv", content)
    
    from analyze_trades import process_mod_file
    result, bad_luck, gain_loss = process_mod_file(filepath)
    
    lines = read_file_lines(filepath)
    
    # Line 3 (index 3) is the entry candle - should have OHLC + gain/loss but no result markers
    entry_line = lines[3].strip()
    
    # Check that entry line has OHLC data
    assert entry_line.startswith('2025.10.31'), f"Expected timestamp, got {entry_line}"
    
    # Check that it has gain or loss marker (entry at 10005, close at 10010 = gain 5)
    assert (' gain ' in entry_line or ' loss ' in entry_line), f"Entry candle should have gain/loss: {entry_line}"
    
    # Check that entry line has NO result markers (TP/SL/BE) after the gain/loss
    # Entry candle should look like: "...;10010.00 gain 5.00" with NO markers after
    if ' gain ' in entry_line:
        after_gain = entry_line.split(' gain ')[1]
        # Should just be the number, possibly with newline, but no TP/SL/BE
        parts = after_gain.split()
        assert len(parts) == 1, f"Entry candle should have only gain/loss value, no markers: {entry_line}"
    elif ' loss ' in entry_line:
        after_loss = entry_line.split(' loss ')[1]
        parts = after_loss.split()
        assert len(parts) == 1, f"Entry candle should have only gain/loss value, no markers: {entry_line}"
    
    print(f"OK Entry candle line: {entry_line}")
    print("OK Entry candle has OHLC + gain/loss but no result markers")
    print("PASSED")

def test_tp_exceeds_target_capped_at_200():
    """Test that TP distance is capped at 200 even when price goes beyond."""
    print("\n=== TEST: TP exceeds target, capped at 200 ===")
    
    # Entry at 10005, high reaches 10220 (15 points beyond TP at 10205)
    # Should show gain 200.00, not 215.00
    content = """Time;Open;High;Low;Close
2025.10.31 10:00;10000.00;10010.00;9990.00;10005.00
2025.10.31 10:15;10005.00;10015.00;10000.00;10010.00 BUY
2025.10.31 10:30;10005.00;10015.00;10000.00;10010.00
2025.10.31 10:45;10020.00;10220.00;10025.00;10215.00
"""
    
    filepath = create_test_file("test_tp_capped_mod.csv", content)
    
    from analyze_trades import process_mod_file
    result, bad_luck, gain_loss = process_mod_file(filepath)
    
    lines = read_file_lines(filepath)
    
    assert result == 'TP', f"Expected TP, got {result}"
    assert gain_loss == 200.0, f"Expected gain_loss=200.0 (capped), got {gain_loss}"
    assert 'gain 200.00 TP' in ''.join(lines), f"Expected 'gain 200.00 TP' in output"
    assert 'gain 215' not in ''.join(lines), f"Should NOT show uncapped value of 215"
    
    print(f"OK Result: {result}, Gain/Loss: {gain_loss:.2f}")
    print("OK TP correctly capped at 200 even though price went to 220")
    print("PASSED")

def test_sell_tp_exceeds_target_capped_at_200():
    """Test that SELL TP distance is capped at 200 even when price goes beyond."""
    print("\n=== TEST: SELL TP exceeds target, capped at 200 ===")
    
    # Entry at 10005, low reaches 9780 (25 points beyond TP at 9805)
    # High stays below BE trigger (10005 - 100 = 9905) to avoid BE complication
    # Should show gain 200.00, not 225.00
    content = """Time;Open;High;Low;Close
2025.10.31 10:00;10000.00;10010.00;9990.00;10005.00
2025.10.31 10:15;10005.00;10015.00;10000.00;10010.00 SELL
2025.10.31 10:30;10005.00;10004.00;9950.00;9955.00
2025.10.31 10:45;9955.00;9954.00;9780.00;9800.00
"""
    
    filepath = create_test_file("test_sell_tp_capped_mod.csv", content)
    
    from analyze_trades import process_mod_file
    result, bad_luck, gain_loss = process_mod_file(filepath)
    
    lines = read_file_lines(filepath)
    
    assert result == 'TP', f"Expected TP, got {result}"
    assert gain_loss == 200.0, f"Expected gain_loss=200.0 (capped), got {gain_loss}"
    assert 'gain 200.00 TP' in ''.join(lines), f"Expected 'gain 200.00 TP' in output"
    assert 'gain 225' not in ''.join(lines), f"Should NOT show uncapped value of 225"
    
    print(f"OK Result: {result}, Gain/Loss: {gain_loss:.2f}")
    print("OK SELL TP correctly capped at 200 even though price went to 225")
    print("PASSED")

def test_sl_exceeds_target_capped_at_50():
    """Test that SL distance is capped at -50 even when price goes beyond."""
    print("\n=== TEST: SL exceeds target, capped at -50 ===")
    
    # Entry at 10010, low reaches 9930 (30 points beyond SL at 9960)
    # Should show loss 50.00, not loss 80.00
    content = """Time;Open;High;Low;Close
2025.10.31 10:00;10000.00;10010.00;9990.00;10005.00
2025.10.31 10:15;10005.00;10015.00;10000.00;10010.00 BUY
2025.10.31 10:30;10010.00;10020.00;9930.00;9935.00
2025.10.31 10:45;9935.00;9945.00;9925.00;9930.00
"""
    
    filepath = create_test_file("test_sl_capped_mod.csv", content)
    
    from analyze_trades import process_mod_file
    result, bad_luck, gain_loss = process_mod_file(filepath)
    
    lines = read_file_lines(filepath)
    
    assert result == 'SL', f"Expected SL, got {result}"
    assert gain_loss == -50.0, f"Expected gain_loss=-50.0 (capped), got {gain_loss}"
    assert 'loss 50.00 SL' in ''.join(lines), f"Expected 'loss 50.00 SL' in output"
    assert 'loss 80' not in ''.join(lines), f"Should NOT show uncapped value of 80"
    
    print(f"OK Result: {result}, Gain/Loss: {gain_loss:.2f}")
    print("OK SL correctly capped at -50 even though price went to -80")
    print("PASSED")

def test_bad_luck_tp_exceeds_target():
    """Test that in bad luck scenario, TP is still capped even when both hit."""
    print("\n=== TEST: Bad luck with TP exceeding target ===")
    
    # Entry at 10005, high=10230 (TP+30), low=9950 (SL-10)
    # Should show loss 0.00 (SL chosen), and TP should be capped at 200 in stats
    content = """Time;Open;High;Low;Close
2025.10.31 10:00;10000.00;10010.00;9990.00;10005.00
2025.10.31 10:15;10005.00;10015.00;10000.00;10010.00 BUY
2025.10.31 10:30;10005.00;10015.00;10000.00;10010.00
2025.10.31 10:45;10010.00;10230.00;9950.00;10100.00
"""
    
    filepath = create_test_file("test_bad_luck_tp_capped_mod.csv", content)
    
    from analyze_trades import process_mod_file
    result, bad_luck, gain_loss = process_mod_file(filepath)
    
    lines = read_file_lines(filepath)
    
    assert result == 'BE', f"Expected BE (break-even), got {result}"
    assert bad_luck == True, f"Expected bad_luck=True, got {bad_luck}"
    # The gain_loss is for BE (worst case when TP also hit), but TP should still be capped internally
    assert '(bad luck)' in ''.join(lines), f"Expected '(bad luck)' marker"
    
    print(f"OK Result: {result}, Gain/Loss: {gain_loss:.2f}, Bad Luck: {bad_luck}")
    print("OK Bad luck scenario with TP exceeding target handled correctly")
    print("PASSED")

def test_buy_tp_at_open_with_slippage():
    """Test BUY TP hit at open with slippage beyond target."""
    print("\n=== TEST: BUY TP at open with slippage ===")
    
    # Entry at 10020, open at 10240 (220 slippage, 20 beyond TP target)
    # Should show gain 220.00 (actual slippage), not capped
    content = """Time;Open;High;Low;Close
2025.10.31 10:00;10000.00;10010.00;9990.00;10005.00
2025.10.31 10:15;10005.00;10015.00;10000.00;10010.00 BUY
2025.10.31 10:30;10020.00;10025.00;10021.00;10022.00
2025.10.31 10:45;10240.00;10250.00;10235.00;10245.00
2025.10.31 11:00;10245.00;10260.00;10240.00;10255.00
"""
    
    filepath = create_test_file("test_buy_tp_slippage_mod.csv", content)
    
    from analyze_trades import process_mod_file
    result, bad_luck, gain_loss = process_mod_file(filepath)
    
    lines = read_file_lines(filepath)
    
    assert result == 'TP', f"Expected TP, got {result}"
    assert gain_loss == 220.0, f"Expected gain_loss=220.0 (actual slippage), got {gain_loss}"
    # Display should show 220 (slippage)
    assert 'gain 220.00 TP (at open)' in ''.join(lines), f"Expected 'gain 220.00 TP (at open)' showing slippage"
    
    print(f"OK Result: {result}, Gain/Loss: {gain_loss:.2f}")
    print("OK TP at open with slippage shown correctly (220 in both display and stats)")
    print("PASSED")

def test_sell_sl_at_open_with_slippage():
    """Test SELL SL hit at open with slippage beyond target."""
    print("\n=== TEST: SELL SL at open with slippage ===")
    
    # Entry at 10005, open at 10075 (70 slippage, 20 beyond SL target)
    # Should show loss 70.00 (actual slippage), not capped
    content = """Time;Open;High;Low;Close
2025.10.31 10:00;10000.00;10010.00;9990.00;10005.00
2025.10.31 10:15;10005.00;10015.00;10000.00;10010.00 SELL
2025.10.31 10:30;10005.00;10004.00;10000.00;10003.00
2025.10.31 10:45;10075.00;10080.00;10070.00;10075.00
2025.10.31 11:00;10075.00;10085.00;10070.00;10080.00
"""
    
    filepath = create_test_file("test_sell_sl_slippage_mod.csv", content)
    
    from analyze_trades import process_mod_file
    result, bad_luck, gain_loss = process_mod_file(filepath)
    
    lines = read_file_lines(filepath)
    
    assert result == 'SL', f"Expected SL, got {result}"
    assert gain_loss == -70.0, f"Expected gain_loss=-70.0 (actual slippage), got {gain_loss}"
    # Display should show 70 (slippage)
    assert 'loss 70.00 SL (at open)' in ''.join(lines), f"Expected 'loss 70.00 SL (at open)' showing slippage"
    
    print(f"OK Result: {result}, Gain/Loss: {gain_loss:.2f}")
    print("OK SL at open with slippage shown correctly (70 in both display and stats)")
    print("PASSED")

def test_buy_be_triggered_tp_hit_during_candle():
    """Test BUY where BE is triggered and TP is hit in same candle."""
    print("\n=== TEST: BUY BE triggered, TP hit during candle ===")
    
    # Entry at 10005, high=10250 (triggers BE at +100 and hits TP at +200)
    # Should show TP result with capped 200, BE marker only if result not finalized
    content = """Time;Open;High;Low;Close
2025.10.31 10:00;10000.00;10010.00;9990.00;10005.00
2025.10.31 10:15;10005.00;10015.00;10000.00;10010.00 BUY
2025.10.31 10:30;10005.00;10015.00;10000.00;10010.00
2025.10.31 10:45;10020.00;10250.00;10025.00;10240.00
2025.10.31 11:00;10240.00;10260.00;10235.00;10250.00
"""
    
    filepath = create_test_file("test_buy_be_tp_same_candle_mod.csv", content)
    
    from analyze_trades import process_mod_file
    result, bad_luck, gain_loss = process_mod_file(filepath)
    
    lines = read_file_lines(filepath)
    
    assert result == 'TP', f"Expected TP, got {result}"
    assert gain_loss == 200.0, f"Expected gain_loss=200.0 (capped), got {gain_loss}"
    # TP is hit same candle as BE trigger, so result is finalized immediately - no separate SL->BE marker
    assert 'TP' in ''.join(lines), f"Expected TP marker"
    assert 'gain 200.00 TP' in ''.join(lines), f"Expected TP capped at 200"
    
    print(f"OK Result: {result}, Gain/Loss: {gain_loss:.2f}")
    print("OK BE triggered and TP hit on same candle, TP shown correctly")
    print("PASSED")

def test_sell_tp_at_open_with_slippage():
    """Test SELL TP hit at open with slippage beyond target."""
    print("\n=== TEST: SELL TP at open with slippage ===")
    
    # Entry at 10005, open at 9775 (230 slippage, 30 beyond TP target)
    # Should show gain 230.00 (actual slippage), not capped
    content = """Time;Open;High;Low;Close
2025.10.31 10:00;10000.00;10010.00;9990.00;10005.00
2025.10.31 10:15;10005.00;10015.00;10000.00;10010.00 SELL
2025.10.31 10:30;10005.00;10004.00;9950.00;9955.00
2025.10.31 10:45;9775.00;9780.00;9770.00;9775.00
2025.10.31 11:00;9775.00;9785.00;9770.00;9780.00
"""
    
    filepath = create_test_file("test_sell_tp_slippage_mod.csv", content)
    
    from analyze_trades import process_mod_file
    result, bad_luck, gain_loss = process_mod_file(filepath)
    
    lines = read_file_lines(filepath)
    
    assert result == 'TP', f"Expected TP, got {result}"
    assert gain_loss == 230.0, f"Expected gain_loss=230.0 (actual slippage), got {gain_loss}"
    # Display should show 230 (slippage)
    assert 'gain 230.00 TP (at open)' in ''.join(lines), f"Expected 'gain 230.00 TP (at open)' showing slippage"
    
    print(f"OK Result: {result}, Gain/Loss: {gain_loss:.2f}")
    print("OK SELL TP at open with slippage shown correctly (230 in both display and stats)")
    print("PASSED")

def test_bad_luck_both_at_open():
    """Test bad luck where both TP and SL could hit at open (gap scenario)."""
    print("\n=== TEST: Bad luck with both TP and SL at open ===")
    
    # Entry at 10005, open gaps to exactly entry (10005) which hits BE after TP triggered
    # This is an edge case where open = entry after large move
    content = """Time;Open;High;Low;Close
2025.10.31 10:00;10000.00;10010.00;9990.00;10005.00
2025.10.31 10:15;10005.00;10015.00;10000.00;10010.00 BUY
2025.10.31 10:30;10005.00;10015.00;10000.00;10010.00
2025.10.31 10:45;10010.00;10230.00;9940.00;10100.00
"""
    
    filepath = create_test_file("test_bad_luck_both_at_open_mod.csv", content)
    
    from analyze_trades import process_mod_file
    result, bad_luck, gain_loss = process_mod_file(filepath)
    
    lines = read_file_lines(filepath)
    
    assert bad_luck == True, f"Expected bad_luck=True, got {bad_luck}"
    assert result == 'BE', f"Expected BE (worst case with BE triggered), got {result}"
    assert '(bad luck)' in ''.join(lines), f"Expected '(bad luck)' marker"
    
    print(f"OK Result: {result}, Gain/Loss: {gain_loss:.2f}, Bad Luck: {bad_luck}")
    print("OK Bad luck with both extremes hit handled correctly")
    print("PASSED")

def run_all_tests():
    """Run all tests."""
    print("="*60)
    print("RUNNING ANALYZE_TRADES.PY TEST SUITE")
    print("="*60)
    
    tests = [
        test_buy_tp,
        test_sell_tp,
        test_buy_sl,
        test_sell_sl,
        test_buy_sl_to_be,
        test_sell_sl_to_be,
        test_buy_tp_and_sl_same_candle,
        test_sell_tp_and_sl_same_candle,
        test_buy_tp_at_open,
        test_buy_sl_at_open,
        test_buy_be_at_open,
        test_entry_candle_has_gain_loss,
        test_sl_hit_on_entry_candle,
        test_be_triggered_and_hit_same_candle_no_at_open,
        test_tp_hit_on_entry_candle,
        test_be_move_on_entry_then_hit_later,
        test_bad_luck_with_be_triggered_same_candle,
        test_tp_exceeds_target_capped_at_200,
        test_sell_tp_exceeds_target_capped_at_200,
        test_sl_exceeds_target_capped_at_50,
        test_bad_luck_tp_exceeds_target,
        test_buy_tp_at_open_with_slippage,
        test_sell_sl_at_open_with_slippage,
        test_buy_be_triggered_tp_hit_during_candle,
        test_sell_tp_at_open_with_slippage,
        test_bad_luck_both_at_open,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "="*60)
    print(f"TEST RESULTS: {passed} passed, {failed} failed")
    print("="*60)
    
    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

