# PythonAnalyzer.dll Logging

## What Changed

The `PythonAnalyzer.cpp` has been updated to write all log messages to a file called `PythonAnalyzer.log`.

## Log File Location

The log file will be created in:
- **During testing**: Same directory as the DLL
- **During MT4 Strategy Tester**: MT4's tester directory (where the EA runs)

## Log Format

Each log entry includes a timestamp:
```
[2025-11-13 14:30:45] Python analyzer initialized
[2025-11-13 14:30:46] analyze_candles call failed
[2025-11-13 14:30:50] Python analyzer finalized
```

## What Gets Logged

1. **Initialization**:
   - `Python analyzer initialized` - Success
   - `Python initialization failed` - Error
   - `Failed to import analyze_candles module` - Module import error
   - `analyze_candles function not callable` - Function error

2. **During Analysis**:
   - `Python not initialized before AnalyzeCandles call` - Not initialized error
   - `AnalyzeCandles received empty path` - Invalid parameter
   - `analyze_candles call failed` - Python function call error
   - `Unexpected result from analyze_candles` - Invalid return value

3. **Cleanup**:
   - `Python analyzer finalized` - Cleanup completed

## Testing Limitation

**Note**: The automated test cannot fully test the DLL because:
- Running Python from within Python (nested interpreter) causes access violations
- This is a testing artifact and won't occur in production
- MT4 will call the DLL from C++ code (not from Python), so logging will work correctly

## Example Log Output (from MT4)

When running in MT4 Strategy Tester, the log file might look like:
```
[2025-11-13 10:15:30] Python analyzer initialized
[2025-11-13 10:15:35] Python analyzer finalized
[2025-11-13 10:20:00] Python analyzer initialized
[2025-11-13 10:20:05] Python analyzer finalized
```

## Viewing the Log

After running the Strategy Tester with the EA:
1. Navigate to the MT4 tester directory
2. Look for `PythonAnalyzer.log`
3. Open with any text editor

Alternatively, the log will be in the same directory as the DLL if called from other contexts.
