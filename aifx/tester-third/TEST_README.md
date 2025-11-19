# Trading System Test Suite

## Overview
Comprehensive test suite for `process_candles.py` and `analyze_trades.py` scripts.

## Running the Tests

```powershell
python test_scripts.py
```

## Test Coverage

### Test 1: Signal Generation
- ✓ Tests BUY/SELL signal assignment based on even/odd integer part of open price
- ✓ Covers forex prices (1.08xxx) and index prices (25404.xx)
- ✓ Tests edge cases (0 is even)

### Test 2: Distance Calculations
- ✓ Tests TP/SL distance calculations for BUY signals
- ✓ Tests TP/SL distance calculations for SELL signals
- ✓ Verifies correct sign handling (positive for favorable, negative for unfavorable)
- ✓ Tests various price movement scenarios

### Test 3: Break-Even Logic
- ✓ Tests BE trigger at +100 points
- ✓ Verifies BE not triggered before threshold
- ✓ Confirms BE remains triggered after threshold

### Test 4: BAD LUCK Detection
- ✓ Tests scenario where both TP and SL are reachable in same candle
- ✓ Verifies only TP reachable (no BAD LUCK)
- ✓ Verifies only SL reachable (no BAD LUCK)
- ✓ Tests for both BUY and SELL signals
- ✓ Uses realistic index-style prices (25400 range)

### Test 5: Close Price Calculation
- ✓ Tests gain/loss calculation when no TP/SL/BE hit
- ✓ Verifies BUY signal close price calculation
- ✓ Verifies SELL signal close price calculation (with negative entry storage)
- ✓ Tests GAIN, LOSS, and BREAK EVEN scenarios

### Test 6: File Processing Integration
- ✓ Creates temporary test files
- ✓ Verifies Volume column removal
- ✓ Verifies BUY/SELL signal addition
- ✓ Checks file format (5 columns header, signal appended to first data line)
- ✓ Confirms _mod file creation
- ✓ Auto-cleanup of test files

### Test 7: Revert Functionality
- ✓ Tests revert_mod_file() function
- ✓ Verifies analysis data removal
- ✓ Confirms BUY/SELL signal preservation
- ✓ Documents expected behavior with signal line markers

## Test Results Summary
- **Total Tests:** 7 test suites
- **Total Assertions:** 36+ individual checks
- **Current Status:** All tests passing ✓

## Key Testing Principles

1. **Realistic Data:** Tests use actual price ranges from the dataset
   - Forex: 1.08xxx range
   - Index: 25400 range

2. **Edge Cases:** Tests cover:
   - Zero distances
   - Negative distances
   - Exact threshold values
   - BAD LUCK scenarios

3. **Integration:** Tests verify end-to-end workflow:
   - File creation → Processing → Verification → Cleanup

4. **Isolation:** Each test creates temporary files and cleans up after itself

## Interpreting Results

### Successful Run
```
============================================================
Total: 7 tests
Passed: 7
Failed: 0
============================================================
```

### Failed Test
If a test fails, the output shows:
- ✗ FAIL marker
- Expected vs actual values
- Detailed diagnostic information

## Notes

- Tests run in isolated temporary directories
- Original data files are never modified
- Test execution is deterministic and repeatable
- Tests can be run multiple times without side effects

## Maintenance

When modifying the trading scripts, run the test suite to ensure:
1. Signal generation remains correct
2. Distance calculations are accurate
3. BAD LUCK detection works properly
4. Close price fallback functions correctly
5. File processing maintains format integrity

## Future Enhancements

Potential additions to test suite:
- Performance tests for large file sets
- Edge case tests for malformed CSV files
- Tests for summary statistics accuracy
- Concurrency tests for parallel processing
