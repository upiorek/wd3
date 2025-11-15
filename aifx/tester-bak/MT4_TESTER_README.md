# MT4 Strategy Tester - Fully Automated Command Line Testing

## Overview
This package provides **fully automated** MT4 strategy testing from the command line:
1. **RandomTrader.mq4** - Simple Expert Advisor that randomly buys/sells on US100.f
2. **mt4_tester.py** - Automated Python script that configures and launches MT4 tests

## ✨ Key Features
- ✅ **Fully Automated** - One command runs the entire test
- ✅ **Command Line** - No manual MT4 configuration needed
- ✅ **Date Parameter** - Specify test date via command line
- ✅ **Auto-Launch** - Automatically opens MT4 with test configured
- ✅ **Report Generation** - Creates timestamped HTML reports
- ✅ **Visual Mode** - Optional visual testing to watch trades

## 🚀 Quick Start (Fully Automated!)

### 1. First-Time Setup

Copy `RandomTrader.mq4` to your MT4 Experts folder and compile it:

**Option A - Manual:**
1. Copy `RandomTrader.mq4` to: `C:\Program Files (x86)\mForex Trader\MQL4\Experts\`
2. Open MT4 → Press **F4** (MetaEditor) → Open `RandomTrader.mq4` → Press **F7** (Compile)

**Option B - Let the script try to copy it:**
Just run the script, it will attempt to auto-copy the EA file.

### 2. Run Automated Tests

**Simplest usage (fully automated with default date):**
```bash
python mt4_tester.py
```
This will:
- Use a date 3 days ago
- Configure MT4 Strategy Tester
- Launch MT4 with the test running automatically
- Generate a report when complete

**Test specific date (fully automated):**
```bash
python mt4_tester.py --date 2025-11-09
```

**Test with visual mode (watch trades happen):**
```bash
python mt4_tester.py --date 2025-11-09 --visual
```

**Test with auto-shutdown (closes MT4 when done):**
```bash
python mt4_tester.py --date 2025-11-09 --shutdown
```

**Full control over all parameters:**
```bash
python mt4_tester.py --symbol US100.f --timeframe 15 --date 2025-11-09 --lot 0.02 --interval 3 --visual
```

### 3. View Results

After the test completes, check for the HTML report:
- Reports are saved in MT4's directory
- Named like: `RandomTrader_Report_20251112_143025.htm`
- Open in any web browser to view detailed results

## 📋 Command-Line Options

### Complete Reference

| Argument | Description | Default |
|----------|-------------|---------|
| `--mt4-path` | Path to terminal.exe | `C:\Program Files (x86)\mForex Trader\terminal.exe` |
| `--symbol` | Trading symbol | `US100.f` |
| `--timeframe` | Timeframe in minutes | `15` (M15) |
| `--date` | Test date (YYYY-MM-DD) | 3 days ago |
| `--lot` | Lot size | `0.01` |
| `--interval` | Candles between trades | `5` |
| `--ea-name` | EA name | `RandomTrader` |
| `--visual` | Enable visual mode | `False` |
| `--shutdown` | Auto-shutdown after test | `False` |
| `--wait` | Wait for test completion and generate report | `False` |
| `--generate-report` | Generate report from most recent test | `False` |
| `--report-timeout` | Timeout when waiting for report (seconds) | `300` |
| `--no-launch` | Generate config only | `False` |
| `--launch-only` | Just launch MT4 | `False` |

### Usage Examples

**Automated test with default settings:**
```bash
python mt4_tester.py
```

**Test specific date:**
```bash
python mt4_tester.py --date 2025-11-09
```

**Visual mode (watch the trades):**
```bash
python mt4_tester.py --date 2025-11-09 --visual
```

**Larger lot size:**
```bash
python mt4_tester.py --date 2025-11-09 --lot 0.1
```

**More frequent trading (every 3 candles):**
```bash
python mt4_tester.py --date 2025-11-09 --interval 3
```

**Different symbol:**
```bash
python mt4_tester.py --symbol EURUSD --date 2025-11-09
```

**Auto-shutdown when complete:**
```bash
python mt4_tester.py --date 2025-11-09 --shutdown
```

**Wait for test to complete and generate report:**
```bash
python mt4_tester.py --date 2025-11-09 --wait
```

**Wait for test with custom timeout (10 minutes):**
```bash
python mt4_tester.py --date 2025-11-09 --wait --report-timeout 600
```

**Generate report from a completed test:**
```bash
python mt4_tester.py --generate-report
```

**Generate config but don't launch:**
```bash
python mt4_tester.py --date 2025-11-09 --no-launch
```

**Complex example:**
```bash
python mt4_tester.py --symbol US100.f --timeframe 15 --date 2025-11-09 --lot 0.05 --interval 3 --visual --shutdown --wait
```

## 📊 Report Generation

The script now includes **automatic report generation** features:

### Option 1: Wait for Test Completion
```bash
python mt4_tester.py --date 2025-11-09 --shutdown --wait
```
This will:
- Launch MT4 and run the test
- Wait for the test to complete (up to 5 minutes by default)
- Automatically find and parse the MT4 HTML report
- Generate a formatted text report with key metrics
- Save the report to a `.txt` file

### Option 2: Generate Report Later
If you already ran a test:
```bash
python mt4_tester.py --generate-report
```
This will:
- Search for recent MT4 reports (last 24 hours)
- Parse the most recent report
- Generate and display a formatted summary
- Save to a text file

### Report Contents
The generated report includes:
- **Performance Summary**: Net profit, gross profit/loss, profit factor
- **Drawdown Analysis**: Absolute, maximal, and relative drawdown
- **Trading Statistics**: Total trades, win/loss ratio, long/short positions
- **Trade Analysis**: Largest profit/loss, average profit/loss, consecutive wins/losses
- **Test Configuration**: Symbol, timeframe, date range, lot size, etc.

### Example Report Output
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
```

## 🔧 Expert Advisor Details

### RandomTrader.mq4

**What it does:**
- Trades on US100.f symbol
- Uses M15 timeframe
- Randomly buys OR sells 0.01 lot every 5 candles
- Tests over 3-day period from specified date

**Input Parameters:**
- `TestDate` - Test date in YYYY-MM-DD format (e.g., "2025-11-09")
- `CandleInterval` - Number of M15 candles between trades (default: 5)
- `LotSize` - Trade volume (default: 0.01)
- `MagicNumber` - Unique identifier for EA trades (default: 123456)

**Features:**
- Random buy/sell decision using MT4's MathRand()
- Detailed logging of each trade
- Error handling with descriptive messages
- Trade counter to track total executions

## 🔄 How It Works (Behind the Scenes)

The Python script automates MT4 testing using MT4's configuration file feature:

1. **Generates Configuration Files:**
   - Creates `.ini` file with Strategy Tester settings
   - Creates `.set` file with EA parameters
   - Both use MT4's native configuration format

2. **Copies Files:**
   - Attempts to copy EA to MT4's Experts folder
   - Copies preset to MT4's tester folder

3. **Launches MT4:**
   - Runs: `terminal.exe config_file.ini`
   - MT4 reads the config and automatically:
     - Loads the EA
     - Configures Strategy Tester
     - Starts the backtest

4. **Generates Report:**
   - MT4 creates HTML report when test completes
   - Report includes all trades, statistics, and charts

## 📊 Understanding Results

After the test completes, open the generated HTML report to see:
- **Total Trades** - Number of buy/sell operations
- **Profit/Loss** - Total P&L for the test period
- **Win Rate** - Percentage of profitable trades
- **Graph** - Visual representation of equity curve
- **Trade List** - Detailed list of every trade executed

## 🔍 Troubleshooting

**MT4 doesn't start the test automatically:**
- Ensure EA is compiled (.ex4 file exists)
- Check that RandomTrader.mq4 is in the Experts folder
- Make sure auto-trading is enabled in MT4 (Tools → Options → Expert Advisors)
- Verify the symbol name matches (US100.f vs US100 vs NAS100)

**EA not showing in Strategy Tester:**
- Copy `RandomTrader.mq4` to: `C:\Program Files (x86)\mForex Trader\MQL4\Experts\`
- Open MetaEditor (F4 in MT4), open the file, press F7 to compile
- Restart MT4

**Symbol not found:**
- Your broker may use different symbol names:
  - `US100` instead of `US100.f`
  - `NAS100` for Nasdaq 100
  - Check Market Watch in MT4 for exact name
- Update command: `python mt4_tester.py --symbol YOUR_SYMBOL_NAME`

**No trades executed:**
- Check MT4 Experts tab for error messages
- Verify the date range has historical data (M15 bars)
- Ensure "Allow automated trading" is checked in Strategy Tester
- Check account balance is sufficient ($10,000 default)

**Wrong MT4 path:**
- Find your terminal.exe location
- Update command: `python mt4_tester.py --mt4-path "C:\Your\Path\terminal.exe"`

**Python script errors:**
- Verify Python 3.6 or higher is installed
- Check date format is YYYY-MM-DD
- Ensure you have write permissions in current directory

## 🚀 Advanced Usage

### Batch Testing Multiple Dates

Create a batch script to test multiple dates:

**test_multiple_dates.bat:**
```batch
@echo off
python mt4_tester.py --date 2025-11-01 --shutdown
timeout /t 60
python mt4_tester.py --date 2025-11-05 --shutdown
timeout /t 60
python mt4_tester.py --date 2025-11-09 --shutdown
```

### Testing Different Parameters

Test with varying lot sizes:
```bash
python mt4_tester.py --date 2025-11-09 --lot 0.01 --shutdown
python mt4_tester.py --date 2025-11-09 --lot 0.05 --shutdown
python mt4_tester.py --date 2025-11-09 --lot 0.10 --shutdown
```

Test with different intervals:
```bash
python mt4_tester.py --date 2025-11-09 --interval 3 --shutdown
python mt4_tester.py --date 2025-11-09 --interval 5 --shutdown
python mt4_tester.py --date 2025-11-09 --interval 10 --shutdown
```

## 📈 Next Steps

To enhance this system, you could:
1. Add more sophisticated trading logic to the EA
2. Implement proper stop-loss and take-profit
3. Add optimization parameters
4. Parse reports and compare multiple test runs
5. Build a batch testing system for multiple dates/parameters
6. Create charts and visualizations from report data
7. Export results to CSV for further analysis

## 🆕 Changelog

**v1.1 (2025-11-12):**
- ✅ Added automatic report generation
- ✅ New `--wait` flag to wait for test completion
- ✅ New `--generate-report` flag to parse existing reports
- ✅ Report parsing from MT4 HTML output
- ✅ Formatted text report with key metrics
- ✅ Automatic report file detection and saving

**v1.0 (Initial Release):**
- ✅ Automated MT4 test configuration
- ✅ Command-line date parameter
- ✅ Auto-launch MT4 with config
- ✅ RandomTrader EA implementation
