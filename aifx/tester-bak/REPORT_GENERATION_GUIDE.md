# MT4 Test Report Generation Guide

## Overview

The MT4 tester script now includes **automatic report generation** that parses MT4's HTML reports and creates formatted text summaries with all key trading metrics.

## 🎯 Quick Usage

### Method 1: Run Test and Wait for Report
The easiest way - run a test and automatically generate a report when complete:

```bash
python mt4_tester.py --date 2025-11-12 --shutdown --wait
```

This command will:
1. ✅ Launch MT4 with the configured test
2. ✅ Wait for the test to complete (up to 5 minutes)
3. ✅ Automatically find the generated MT4 HTML report
4. ✅ Parse the report and extract key metrics
5. ✅ Display a formatted summary in the terminal
6. ✅ Save the report to a timestamped text file

### Method 2: Generate Report from Existing Test
If you already ran a test and want to generate a report:

```bash
python mt4_tester.py --generate-report
```

This will:
1. ✅ Search for recent MT4 reports (last 24 hours)
2. ✅ Parse the most recent report
3. ✅ Display and save a formatted summary

## 📊 Report Contents

The generated report includes comprehensive trading statistics:

### Performance Summary
- **Initial Deposit** - Starting account balance
- **Final Balance** - Ending account balance
- **Total Net Profit** - Overall profit/loss
- **Gross Profit** - Total profit from winning trades
- **Gross Loss** - Total loss from losing trades
- **Profit Factor** - Ratio of gross profit to gross loss
- **Expected Payoff** - Average profit/loss per trade

### Drawdown Analysis
- **Absolute Drawdown** - Maximum loss from initial deposit
- **Maximal Drawdown** - Largest peak-to-trough decline
- **Relative Drawdown** - Drawdown as percentage of equity

### Trading Statistics
- **Total Trades** - Number of trades executed
- **Long Positions** - Buy trades and win rate
- **Short Positions** - Sell trades and win rate
- **Profit Trades** - Winning trades count and percentage
- **Loss Trades** - Losing trades count and percentage

### Trade Analysis
- **Largest Profit** - Biggest winning trade
- **Largest Loss** - Biggest losing trade
- **Average Profit** - Average winning trade size
- **Average Loss** - Average losing trade size
- **Max Consecutive Wins** - Longest winning streak
- **Max Consecutive Losses** - Longest losing streak

### Test Configuration
- **Expert Advisor** - EA name used
- **Symbol** - Trading instrument
- **Timeframe** - Chart period
- **Test Period** - Date range tested
- **Lot Size** - Trade volume
- **Candle Interval** - Trading frequency

## 🔧 Command Options

### --wait
Wait for test completion and generate report:
```bash
python mt4_tester.py --date 2025-11-12 --wait
```

### --report-timeout
Customize wait timeout (default 300 seconds):
```bash
python mt4_tester.py --date 2025-11-12 --wait --report-timeout 600
```

### --generate-report
Generate report from existing test:
```bash
python mt4_tester.py --generate-report
```

### --shutdown
Auto-close MT4 after test (recommended with --wait):
```bash
python mt4_tester.py --date 2025-11-12 --shutdown --wait
```

## 📝 Example Report Output

```
======================================================================
MT4 STRATEGY TEST REPORT
======================================================================

Generated: 2025-11-12 16:30:45
Source: RandomTrader_Report_20251112_154808.htm

──────────────────────────────────────────────────────────────────────
TEST CONFIGURATION
──────────────────────────────────────────────────────────────────────
Expert Advisor:      RandomTrader
Symbol:              US100.f
Timeframe:           M15
Test Period:         2025-11-09 to 2025-11-12
Lot Size:            0.01
Candle Interval:     5

──────────────────────────────────────────────────────────────────────
PERFORMANCE SUMMARY
──────────────────────────────────────────────────────────────────────
Initial Deposit:     $10000.00
Final Balance:       $9987.50
Total Net Profit:    $-12.50
Gross Profit:        $450.00
Gross Loss:          $-462.50
Profit Factor:       0.97
Expected Payoff:     $-0.69

──────────────────────────────────────────────────────────────────────
DRAWDOWN ANALYSIS
──────────────────────────────────────────────────────────────────────
Absolute Drawdown:   $12.50
Maximal Drawdown:    $125.00 (1.25%)
Relative Drawdown:   1.25% ($125.00)

──────────────────────────────────────────────────────────────────────
TRADING STATISTICS
──────────────────────────────────────────────────────────────────────
Total Trades:        18
Long Positions:      9 (44.44% won)
Short Positions:     9 (55.56% won)
Profit Trades:       9 (50.00%)
Loss Trades:         9 (50.00%)

──────────────────────────────────────────────────────────────────────
TRADE ANALYSIS
──────────────────────────────────────────────────────────────────────
Largest Profit:      $85.00
Largest Loss:        $-92.50
Average Profit:      $50.00
Average Loss:        $-51.39
Max Consecutive Wins:   3
Max Consecutive Losses: 4

──────────────────────────────────────────────────────────────────────
REPORT FILES
──────────────────────────────────────────────────────────────────────
HTML Report:         C:\...\Terminal\...\tester\reports\RandomTrader_Report_20251112_154808.htm

======================================================================
```

## 🔄 Complete Workflow Examples

### Quick Test with Report
```bash
# Run test for today and get immediate report
python mt4_tester.py --date 2025-11-12 --shutdown --wait
```

### Visual Test with Report
```bash
# Watch the test run and get report when done
python mt4_tester.py --date 2025-11-12 --visual --wait
```

### Background Test with Later Report
```bash
# Start test in background
python mt4_tester.py --date 2025-11-12

# Generate report later (when test completes)
python mt4_tester.py --generate-report
```

### Custom Parameters with Report
```bash
# Test with specific settings and get report
python mt4_tester.py --symbol US100.f --timeframe 15 --date 2025-11-12 \
    --lot 0.02 --interval 3 --shutdown --wait
```

### Batch Testing with Reports
```bash
# Test multiple dates and generate reports
python mt4_tester.py --date 2025-11-09 --shutdown --wait
python mt4_tester.py --date 2025-11-10 --shutdown --wait
python mt4_tester.py --date 2025-11-11 --shutdown --wait
```

## 📂 Output Files

### Generated Report Files
Reports are saved with timestamps in the current directory:
- Format: `mt4_test_report_YYYYMMDD_HHMMSS.txt`
- Example: `mt4_test_report_20251112_163045.txt`

### MT4 HTML Reports
MT4 generates HTML reports in its tester directory:
- Location: `C:\Users\[User]\AppData\Roaming\MetaQuotes\Terminal\[ID]\tester\reports\`
- Format: `RandomTrader_Report_YYYYMMDD_HHMMSS.htm`
- These can be opened in any web browser for detailed analysis

## 🐛 Troubleshooting

### "No recent MT4 reports found"
**Problem:** Script can't find any MT4 report files

**Solutions:**
1. Ensure a test has actually been run
2. Check that MT4 is configured to generate reports
3. Verify the test completed successfully
4. Look for reports manually in MT4's tester/reports folder
5. Try increasing the search time: the script looks for reports from the last 24 hours

### Report Timeout
**Problem:** `--wait` times out before test completes

**Solutions:**
1. Increase timeout: `--report-timeout 600` (10 minutes)
2. Run test without `--wait`, then use `--generate-report` later
3. Use visual mode `--visual` to see if test is stuck
4. Check MT4 for error messages in the Experts tab

### Incomplete Report Data
**Problem:** Report shows "N/A" for some metrics

**Solutions:**
1. This is normal if MT4's report doesn't include that metric
2. Check the original HTML report for complete data
3. Ensure the test ran long enough to generate meaningful statistics

### Wrong Report Parsed
**Problem:** Script parses an old report instead of the latest one

**Solutions:**
1. The script automatically selects the most recent report
2. Delete old reports from MT4's reports folder if needed
3. Verify test completion by checking MT4's Strategy Tester window

## 💡 Tips and Best Practices

### 1. Always Use --shutdown with --wait
```bash
python mt4_tester.py --date 2025-11-12 --shutdown --wait
```
This ensures MT4 closes after testing, signaling completion.

### 2. Increase Timeout for Long Tests
```bash
python mt4_tester.py --date 2025-11-12 --wait --report-timeout 900
```
Some tests may take longer than the default 5 minutes.

### 3. Save Reports for Comparison
Reports are automatically timestamped, making it easy to compare results:
```bash
ls mt4_test_report_*.txt
```

### 4. Use Visual Mode for Debugging
```bash
python mt4_tester.py --date 2025-11-12 --visual --wait
```
Watch the test execute to identify any issues.

### 5. Test in Batch
Create a script to test multiple configurations and compare results:
```bash
python mt4_tester.py --date 2025-11-12 --lot 0.01 --shutdown --wait
python mt4_tester.py --date 2025-11-12 --lot 0.05 --shutdown --wait
python mt4_tester.py --date 2025-11-12 --lot 0.10 --shutdown --wait
```

## 🎓 Understanding the Metrics

### Profit Factor
- **> 1.0** = Profitable strategy
- **< 1.0** = Losing strategy
- **1.0** = Break-even
- Example: 1.5 means $1.50 profit for every $1.00 loss

### Expected Payoff
- Average profit/loss per trade
- Positive = profitable on average
- Negative = losing on average
- Used to calculate long-term profitability

### Drawdown
- **Absolute**: Max loss from starting balance
- **Maximal**: Largest peak-to-trough decline
- **Relative**: Drawdown as % of peak equity
- Lower is better - indicates risk control

### Win Rate
- Percentage of winning trades
- 50% = break-even for random trading
- Higher is better, but not the only metric
- Must consider profit factor too

## 📚 Next Steps

1. **Compare Results**: Run multiple tests and compare reports
2. **Optimize Parameters**: Test different lot sizes and intervals
3. **Analyze Patterns**: Look for correlations in winning/losing streaks
4. **Export Data**: Parse report files for further analysis
5. **Visualize**: Create charts from report metrics

## 🔗 Related Files

- `mt4_tester.py` - Main testing script
- `RandomTrader.mq4` - Expert Advisor source code
- `MT4_TESTER_README.md` - Complete testing guide
- `mt4_test_config.ini` - Generated configuration file
- `RandomTrader.set` - EA parameter preset

---

**Version:** 1.1  
**Last Updated:** 2025-11-12  
**Author:** Trading System
