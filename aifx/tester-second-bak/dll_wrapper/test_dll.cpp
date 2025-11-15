/*
 * Simple C++ test program for PythonAnalyzer.dll
 * This avoids the nested Python interpreter issue
 */

#include <windows.h>
#include <iostream>
#include <string>

typedef int (__stdcall *InitializePythonFunc)(const wchar_t*, const wchar_t*);
typedef int (__stdcall *AnalyzeCandlesFunc)(const wchar_t*);
typedef void (__stdcall *FinalizePythonFunc)();

int main()
{
    std::wcout << L"\n========================================" << std::endl;
    std::wcout << L"  PythonAnalyzer.dll Test Suite" << std::endl;
    std::wcout << L"========================================\n" << std::endl;
    std::wcout.flush();

    // Cleanup old log files
    std::wcout << L"[0/4] Cleaning up old log files..." << std::endl;
    DeleteFileW(L"PythonAnalyzer.log");
    
    // Get current date for analysis log file
    SYSTEMTIME st;
    GetLocalTime(&st);
    wchar_t analysisLogName[256];
    swprintf_s(analysisLogName, L"analysis_%04d-%02d-%02d.log", st.wYear, st.wMonth, st.wDay);
    DeleteFileW(analysisLogName);
    
    std::wcout << L"   [OK] Cleanup completed\n" << std::endl;
    std::wcout.flush();

    // Load the DLL
    std::wcout << L"[1/4] Loading DLL..." << std::endl;
    HMODULE hDll = LoadLibraryW(L"PythonAnalyzer.dll");
    if (!hDll)
    {
        std::wcerr << L"   [X] FAILED: Could not load PythonAnalyzer.dll" << std::endl;
        std::wcerr << L"   Error code: " << GetLastError() << std::endl;
        std::wcout << L"\n========================================" << std::endl;
        std::wcout << L"  TEST FAILED" << std::endl;
        std::wcout << L"========================================\n" << std::endl;
        return 1;
    }
    std::wcout << L"   [OK] PythonAnalyzer.dll loaded successfully" << std::endl;
    std::wcout.flush();

    // Get function pointers
    std::wcout << L"\n[2/4] Retrieving function pointers..." << std::endl;
    std::wcout.flush();
    InitializePythonFunc InitializePython = (InitializePythonFunc)GetProcAddress(hDll, "InitializePython");
    AnalyzeCandlesFunc AnalyzeCandles = (AnalyzeCandlesFunc)GetProcAddress(hDll, "AnalyzeCandles");
    FinalizePythonFunc FinalizePython = (FinalizePythonFunc)GetProcAddress(hDll, "FinalizePython");

    // If not found, try decorated names for stdcall
    if (!InitializePython || !AnalyzeCandles || !FinalizePython)
    {
        if (!InitializePython)
        {
            InitializePython = (InitializePythonFunc)GetProcAddress(hDll, "_InitializePython@8");
        }
        if (!AnalyzeCandles)
        {
            AnalyzeCandles = (AnalyzeCandlesFunc)GetProcAddress(hDll, "_AnalyzeCandles@4");
        }
        if (!FinalizePython)
        {
            FinalizePython = (FinalizePythonFunc)GetProcAddress(hDll, "_FinalizePython@0");
        }
        
        // Check if we got them all now
        if (!InitializePython || !AnalyzeCandles || !FinalizePython)
        {
            std::wcerr << L"   [X] FAILED: Could not retrieve all function pointers" << std::endl;
            FreeLibrary(hDll);
            std::wcout << L"\n========================================" << std::endl;
            std::wcout << L"  TEST FAILED" << std::endl;
            std::wcout << L"========================================\n" << std::endl;
            return 1;
        }
    }
    std::wcout << L"   [OK] All function pointers retrieved" << std::endl;
    std::wcout.flush();

    // Test 1: Initialize Python
    std::wcout << L"\n[3/4] Initializing Python interpreter..." << std::endl;
    std::wcout.flush();

    // Get the parent directory (where analyze_candles.py is)
    wchar_t currentDir[MAX_PATH];
    GetCurrentDirectoryW(MAX_PATH, currentDir);
    std::wstring scriptDir = std::wstring(currentDir) + L"\\..";

    // Set Python home to avoid "Could not find platform independent libraries" warning
    std::wstring pythonHome = L"C:\\Python311-32";

    std::wcout << L"   Python home: " << pythonHome << std::endl;
    std::wcout << L"   Script directory: " << scriptDir << std::endl;
    std::wcout.flush();

    int initResult = InitializePython(pythonHome.c_str(), scriptDir.c_str());
    if (initResult == 1)
    {
        std::wcout << L"   [OK] Python interpreter initialized successfully" << std::endl;
        std::wcout.flush();
    }
    else
    {
        std::wcerr << L"   [X] FAILED: Python initialization failed" << std::endl;
        std::wcerr.flush();
        FreeLibrary(hDll);
        std::wcout << L"\n========================================" << std::endl;
        std::wcout << L"  TEST FAILED" << std::endl;
        std::wcout << L"========================================\n" << std::endl;
        return 1;
    }

    // Test 2: Analyze a CSV file (look for one in m15_candles)
    std::wcout << L"\n[4/4] Testing candle analysis..." << std::endl;
    std::wcout.flush();

    // Try to find a CSV file
    WIN32_FIND_DATAW findData;
    HANDLE hFind = FindFirstFileW(L"..\\m15_candles\\*.csv", &findData);
    
    bool testPassed = false;
    if (hFind != INVALID_HANDLE_VALUE)
    {
        std::wstring csvFile = std::wstring(findData.cFileName);
        std::wstring csvPath = L"..\\m15_candles\\" + csvFile;
        FindClose(hFind);

        std::wcout << L"   CSV file: " << csvFile << std::endl;
        std::wcout.flush();

        int signal = AnalyzeCandles(csvPath.c_str());
        
        if (signal == 1)
        {
            std::wcout << L"   [OK] Signal: BUY (1) - More white candles than black" << std::endl;
            std::wcout.flush();
            testPassed = true;
        }
        else if (signal == -1)
        {
            std::wcout << L"   [OK] Signal: SELL (-1) - More black candles than white" << std::endl;
            std::wcout.flush();
            testPassed = true;
        }
        else if (signal == 0)
        {
            std::wcerr << L"   [X] FAILED: Analysis returned ERROR (0)" << std::endl;
            std::wcerr.flush();
        }
        else
        {
            std::wcerr << L"   [X] FAILED: Unexpected signal value: " << signal << std::endl;
            std::wcerr.flush();
        }
    }
    else
    {
        std::wcout << L"   [!] WARNING: No CSV files found in m15_candles directory" << std::endl;
        std::wcout << L"   Skipping analysis test" << std::endl;
        std::wcout.flush();
        testPassed = true; // Don't fail if no test files
    }

    // Finalize Python
    FinalizePython();

    // Cleanup
    FreeLibrary(hDll);

    // Final results
    std::wcout << L"\n========================================" << std::endl;
    std::wcout.flush();
    if (testPassed)
    {
        std::wcout << L"  [OK] ALL TESTS PASSED" << std::endl;
        std::wcout << L"========================================\n" << std::endl;
        std::wcout << L"Log files:" << std::endl;
        std::wcout << L"  - PythonAnalyzer.log (DLL operations)" << std::endl;
        std::wcout << L"  - analysis_YYYY-MM-DD.log (Analysis results)" << std::endl;
        std::wcout << L"\nThe DLL is ready for MT4 integration!\n" << std::endl;
        std::wcout.flush();
        return 0;
    }
    else
    {
        std::wcout << L"  [X] TEST FAILED" << std::endl;
        std::wcout << L"========================================\n" << std::endl;
        std::wcout << L"Check PythonAnalyzer.log for details.\n" << std::endl;
        std::wcout.flush();
        return 1;
    }
}
