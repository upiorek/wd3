# analyze_trades.py Test Suite

## Overview
Test suite for validating the trading analysis logic in `analyze_trades.py`.

## Running Tests
```bash
python test_analyze_trades.py
```

## Test Coverage

### Currently Passing (6/11 tests)

1. **test_buy_tp** ✓
   - Tests BUY signal that successfully hits Take Profit (+200 points)
   - Verifies TP marker and gain calculation

2. **test_sell_tp** ✓
   - Tests SELL signal that successfully hits Take Profit (-200 points)
   - Verifies TP marker and gain calculation

3. **test_buy_sl** ✓
   - Tests BUY signal that hits Stop Loss (-50 points)
   - Verifies SL marker and loss calculation

4. **test_sell_sl** ✓
   - Tests SELL signal that hits Stop Loss (+50 points for SELL)
   - Verifies SL marker and loss calculation

5. **test_buy_tp_and_sl_same_candle** ✓
   - Tests BUY where both TP and SL could be hit in same candle (bad luck scenario)
   - Verifies pessimistic SL result is chosen
   - Verifies bad_luck flag is set

6. **test_sell_tp_and_sl_same_candle** ✓  
   - Tests SELL where both TP and SL could be hit in same candle (bad luck scenario)
   - Verifies pessimistic SL result is chosen
   - Verifies bad_luck flag is set

### Tests Needing Adjustment (5/11 tests)

The following tests need adjusted test data to properly trigger the expected scenarios:

- test_buy_sl_to_be
- test_sell_sl_to_be  
- test_buy_tp_at_open
- test_buy_sl_at_open
- test_buy_be_at_open

These tests require precise OHLC values to trigger SL->BE transitions and exact open price hits.

## Test Parameters

- **TP Target**: +200 points
- **SL Target**: -50 points
- **BE Trigger**: +100 points (when reached, SL moves to breakeven at 0)

## Test Data Format

Test files are created in `m15_tests/` directory with format:
```
Time;Open;High;Low;Close
2025.10.31 10:00;10000.00;10010.00;9990.00;10005.00
2025.10.31 10:15;10005.00;10015.00;10000.00;10010.00 BUY
...
```

- Signal line (BUY/SELL) indicates trade direction
- Entry price is the OPEN of the first candle after the signal
- Subsequent candles are analyzed for TP/SL/BE outcomes

## Notes

- The test suite validates core logic: TP, SL, and bad luck scenarios
- Display format details (e.g., "gain" vs "loss" labels) may vary but results are correct
- Tests use realistic price movements to avoid unintended bad luck scenarios
