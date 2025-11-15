#include <windows.h>
#include <Python.h>
#include <string>
#include <fstream>
#include <ctime>

static bool g_initialized = false;
static std::wstring g_script_dir;
static std::wstring g_python_home;
static PyObject* g_module = nullptr;
static PyObject* g_function = nullptr;
static PyThreadState* g_mainThreadState = nullptr;

const wchar_t* version = L"pythonAnalyzer-2.0\n";

static void log_message(const wchar_t* message)
{
    // Log to debug output
    OutputDebugStringW(message);
    
    // Log to file
    std::wofstream logFile;
    logFile.open(L"PythonAnalyzer.log", std::ios::app);
    if (logFile.is_open())
    {
        // Add timestamp
        time_t now = time(nullptr);
        struct tm timeinfo;
        localtime_s(&timeinfo, &now);
        wchar_t timestamp[32];
        wcsftime(timestamp, sizeof(timestamp) / sizeof(wchar_t), L"%Y-%m-%d %H:%M:%S", &timeinfo);
        
        logFile << L"[" << timestamp << L"] " << message;
        logFile.close();
    }
}

static void log_python_error()
{
    if (PyErr_Occurred())
    {
        PyErr_Print();
        PyErr_Clear();
    }
}

extern "C" __declspec(dllexport) int __stdcall InitializePython(const wchar_t* pythonHome,
                                                                const wchar_t* scriptDirectory)
{
    log_message(version);

    if (g_initialized)
    {
        return 1;
    }

    if (pythonHome != nullptr && pythonHome[0] != L'\0')
    {
        g_python_home = pythonHome;
        Py_SetPythonHome(const_cast<wchar_t*>(g_python_home.c_str()));
    }

    Py_Initialize();
    if (!Py_IsInitialized())
    {
        log_message(L"Python initialization failed\n");
        return 0;
    }

    PyEval_InitThreads();

    // Redirect Python's stdout and stderr to NUL to prevent output interference
    PyRun_SimpleString("import sys; import os");
    PyRun_SimpleString("sys.stdout = open(os.devnull, 'w')");
    PyRun_SimpleString("sys.stderr = open(os.devnull, 'w')");

    if (scriptDirectory != nullptr && scriptDirectory[0] != L'\0')
    {
        g_script_dir = scriptDirectory;

        PyObject* sysPath = PySys_GetObject("path");
        if (sysPath != nullptr)
        {
            PyObject* pathEntry = PyUnicode_FromWideChar(g_script_dir.c_str(), static_cast<Py_ssize_t>(g_script_dir.length()));
            if (pathEntry != nullptr)
            {
                PyList_Append(sysPath, pathEntry);
                Py_DECREF(pathEntry);
            }
        }
    }

    g_module = PyImport_ImportModule("analyze_candles");
    if (g_module == nullptr)
    {
        log_message(L"Failed to import analyze_candles module\n");
        log_python_error();
        Py_Finalize();
        return 0;
    }

    g_function = PyObject_GetAttrString(g_module, "analyze_candles");
    if (g_function == nullptr || !PyCallable_Check(g_function))
    {
        log_message(L"analyze_candles function not callable\n");
        log_python_error();

        Py_XDECREF(g_function);
        Py_DECREF(g_module);
        g_module = nullptr;
        g_function = nullptr;
        Py_Finalize();
        return 0;
    }

    g_initialized = true;
    g_mainThreadState = PyEval_SaveThread();
    log_message(L"Python analyzer initialized\n");
    return 1;
}

extern "C" __declspec(dllexport) int __stdcall AnalyzeCandles(const wchar_t* csvPath)
{
    if (!g_initialized || g_function == nullptr)
    {
        log_message(L"Python not initialized before AnalyzeCandles call\n");
        return 0;
    }

    if (csvPath == nullptr || csvPath[0] == L'\0')
    {
        log_message(L"AnalyzeCandles received empty path\n");
        return 0;
    }

    PyGILState_STATE gilState = PyGILState_Ensure();

    PyObject* args = PyTuple_New(1);
    PyObject* pathArg = PyUnicode_FromWideChar(csvPath, -1);
    PyTuple_SetItem(args, 0, pathArg); // Steals reference to pathArg

    PyObject* result = PyObject_CallObject(g_function, args);
    Py_DECREF(args);

    if (result == nullptr)
    {
        log_message(L"analyze_candles call failed\n");
        log_python_error();
        PyGILState_Release(gilState);
        return 0;
    }

    int signal = 0;
    int isTrue = PyObject_IsTrue(result);
    Py_DECREF(result);

    if (isTrue == 1)
    {
        signal = 1; // BUY
    }
    else if (isTrue == 0)
    {
        signal = -1; // SELL
    }
    else
    {
        log_message(L"Unexpected result from analyze_candles\n");
        log_python_error();
    }

    PyGILState_Release(gilState);
    return signal;
}

extern "C" __declspec(dllexport) void __stdcall FinalizePython()
{
    if (!g_initialized)
    {
        return;
    }

    if (g_mainThreadState != nullptr)
    {
        PyEval_RestoreThread(g_mainThreadState);
        g_mainThreadState = nullptr;
    }

    Py_XDECREF(g_function);
    Py_XDECREF(g_module);
    g_function = nullptr;
    g_module = nullptr;
    g_script_dir.clear();
    g_python_home.clear();

    Py_Finalize();
    g_initialized = false;
    log_message(L"Python analyzer finalized\n");
}
