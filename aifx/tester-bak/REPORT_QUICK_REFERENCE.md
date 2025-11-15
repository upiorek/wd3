# MT4 Report Generation - Quick Reference

## 🚀 Most Common Commands

### Run Test and Get Report (Recommended)
```bash
python mt4_tester.py --date 2025-11-12 --shutdown --wait
```
**What it does:** Runs test, closes MT4 when done, generates report automatically

### Generate Report from Existing Test
```bash
python mt4_tester.py --generate-report
```
**What it does:** Finds and parses the most recent MT4 report

### Run Test with Custom Timeout
```bash
python mt4_tester.py --date 2025-11-12 --shutdown --wait --report-timeout 600
```
**What it does:** Waits up to 10 minutes (600 seconds) for test to complete

### Visual Test with Report
```bash
python mt4_tester.py --date 2025-11-12 --visual --wait
```
**What it does:** Shows test execution in MT4 and generates report when done

## 📊 Report Features

✅ **Automatic Detection** - Finds MT4 reports automatically  
✅ **Key Metrics** - Extracts profit, drawdown, win rate, etc.  
✅ **Formatted Output** - Clean, readable text format  
✅ **File Save** - Saves to timestamped .txt file  
✅ **Complete Stats** - All trading statistics included  

## 🔧 New Command Options

| Option | Description | Example |
|--------|-------------|---------|
| `--wait` | Wait for test and generate report | `--wait` |
| `--generate-report` | Parse existing report | `--generate-report` |
| `--report-timeout` | Custom wait timeout (seconds) | `--report-timeout 600` |

## 📈 Report Sections

1. **Test Configuration** - EA, symbol, timeframe, dates, lot size
2. **Performance Summary** - Profit/loss, profit factor, payoff
3. **Drawdown Analysis** - Absolute, maximal, relative drawdown
4. **Trading Statistics** - Total trades, win rate, long/short ratio
5. **Trade Analysis** - Largest/average profit/loss, streaks
6. **Report Files** - Links to HTML and text reports

## ⚡ Quick Workflows

### Workflow 1: Quick Test
```bash
# One command does everything
python mt4_tester.py --date 2025-11-12 --shutdown --wait
```

### Workflow 2: Watch and Report
```bash
# Watch the test, get report at end
python mt4_tester.py --date 2025-11-12 --visual --wait
```

### Workflow 3: Background Test
```bash
# Start test
python mt4_tester.py --date 2025-11-12

# Generate report later
python mt4_tester.py --generate-report
```

### Workflow 4: Batch Testing
```bash
# Test multiple dates automatically
python mt4_tester.py --date 2025-11-09 --shutdown --wait
python mt4_tester.py --date 2025-11-10 --shutdown --wait
python mt4_tester.py --date 2025-11-11 --shutdown --wait
```

## 💡 Pro Tips

✅ Use `--shutdown` with `--wait` for hands-free operation  
✅ Increase timeout for longer tests: `--report-timeout 900`  
✅ Reports are auto-saved with timestamps for easy comparison  
✅ Use `--visual` to debug if test hangs or fails  
✅ Check current directory for `mt4_test_report_*.txt` files  

## 🐛 Common Issues

**"No recent MT4 reports found"**  
→ Make sure a test has been run recently  
→ Check MT4's tester/reports folder manually  

**Timeout waiting for report**  
→ Increase timeout: `--report-timeout 600`  
→ Use visual mode to see what's happening  
→ Run without `--wait`, generate report later  

**Report shows "N/A" values**  
→ Normal if MT4 doesn't provide that metric  
→ Check original HTML report for complete data  

## 📂 Output Files

**Text Report:**  
- Location: Current directory  
- Format: `mt4_test_report_20251112_163045.txt`  
- Content: Formatted text summary  

**HTML Report:**  
- Location: `AppData\Roaming\MetaQuotes\Terminal\...\tester\reports\`  
- Format: `RandomTrader_Report_20251112_154808.htm`  
- Content: Complete MT4 test results with charts  

## 📚 More Information

- Full guide: `REPORT_GENERATION_GUIDE.md`
- Complete documentation: `MT4_TESTER_README.md`
- EA source code: `RandomTrader.mq4`

---

**Version:** 1.1 | **Last Updated:** 2025-11-12
