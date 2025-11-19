PythonAnalyzer DLL
===================

This folder contains the source code for the `PythonAnalyzer.dll` wrapper that lets the
`SaveM15Candles.mq4` expert call into Python while running inside the MT4 Strategy Tester.

Build Requirements
------------------
- Visual Studio 2019 (or newer) with Desktop development with C++ workload installed.
- 32-bit (x86) toolset – MetaTrader 4 loads 32-bit DLLs only.
- CPython development headers and import library that match the Python runtime you want to
  embed (for example Python 3.11 => `python311.dll`, `python311.lib`).

Project Setup
-------------
1. Create a new **Win32 Project** → **DLL** in Visual Studio (x86 target).
2. Replace the auto-generated `dllmain.cpp` with `PythonAnalyzer.cpp` provided here or add
   this file to the project.
3. Under **C/C++ → General → Additional Include Directories**, add the path to the Python
   headers (e.g. `C:\Python311\include`).
4. Under **Linker → General → Additional Library Directories**, add the path to the Python
   library files (e.g. `C:\Python311\libs`).
5. Under **Linker → Input → Additional Dependencies**, append the Python import library
   (e.g. `python311.lib`).
6. Ensure the project’s **Character Set** is **Use Unicode Character Set**.
7. Build the project; the resulting `PythonAnalyzer.dll` should appear in your project's
   `Debug` or `Release` folder.

Testing the DLL
---------------
After building the DLL, you can test it using the provided test script:

```bash
python test_pythonanalyzer_dll.py
```

Or run the batch file:
```bash
test_dll.bat
```

**Note:** The DLL is compiled as 32-bit for MT4 compatibility. If you're running 64-bit
Python, the test will detect the DLL but won't be able to fully test it (architecture
mismatch). The test will confirm the DLL exists and is properly compiled. For full
functional testing, use 32-bit Python.

Deployment
----------
Copy the compiled `PythonAnalyzer.dll` into:
- `%APPDATA%\MetaQuotes\Terminal\<terminal-id>\MQL4\Libraries`
- `%APPDATA%\MetaQuotes\Terminal\<terminal-id>\tester\libraries` (for Strategy Tester)

The `run_strategy_tester.py` helper script will also attempt to copy the DLL from this
folder into the correct MT4 directories before launching the test.

Runtime Expectations
--------------------
- `SaveM15Candles.mq4` calls `InitializePython` during `OnInit`. Provide the Python home
  and script directory via the expert inputs, or leave them blank to use sensible defaults.
- The DLL imports `analyze_candles.py` and invokes its `analyze_candles()` function for each
  CSV file. Return value mapping: `True → BUY`, `False → SELL`, errors → no trade.
- Make sure the Python runtime (`pythonXY.dll`) that you linked against is accessible on the
  test machine (either in `PATH` or alongside the MT4 terminal executable).

Troubleshooting
---------------
- If MT4 logs "cannot load PythonAnalyzer.dll", ensure the build is 32-bit and that all
  runtime dependencies (Python DLLs) are discoverable.
- If initialization fails, enable **Allow DLL imports** in the Strategy Tester settings and
  double-check the Python home/script paths supplied to the EA.
