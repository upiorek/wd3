//+------------------------------------------------------------------+
//|                                              SaveM15Candles.mq4  |
//|                                                                  |
//|  Saves last 10 M15 candles to file on each new candle           |
//+------------------------------------------------------------------+
#property copyright "Copyright 2025"
#property link      ""
#property version   "2.00"
#property strict

// Import Python analyzer DLL (ensure the DLL is located in MQL4\Libraries)
#import "PythonAnalyzer.dll"
   int InitializePython(string pythonHome, string scriptDir);
   int AnalyzeCandles(string csvPath);
   void FinalizePython();
#import

// Specify subdirectory name (will be created in MT4 Files folder)
string FolderName = "m15_candles";

datetime lastBarTime = 0;
string ScriptDirectory = "";

input string PythonHomePath     = "";
input string PythonScriptsDir   = "";

// Settings that can be overridden by settings.txt
int    NumberOfCandles    = 10;  // Number of M15 candles to save and analyze
double StopLossPoints     = 0;   // Stop Loss in points (0 = disabled)
double TakeProfitPoints   = 0;   // Take Profit in points (0 = disabled)

//+------------------------------------------------------------------+
//| Read settings from settings.txt file                             |
//+------------------------------------------------------------------+
void ReadSettingsFile()
{
   string settingsFile = "settings.txt";
   
   if(!FileIsExist(settingsFile, 0))
   {
      Print("Settings file not found: ", settingsFile, " - using default values");
      return;
   }
   
   int fileHandle = FileOpen(settingsFile, FILE_READ|FILE_TXT);
   if(fileHandle == INVALID_HANDLE)
   {
      Print("Error opening settings file. Error code: ", GetLastError());
      return;
   }
   
   Print("Reading settings from: ", settingsFile);
   
   while(!FileIsEnding(fileHandle))
   {
      string line = FileReadString(fileHandle);
      line = StringTrimLeft(StringTrimRight(line));
      
      // Skip empty lines and comments
      if(StringLen(line) == 0 || StringGetCharacter(line, 0) == ';' || StringGetCharacter(line, 0) == '#')
         continue;
      
      // Parse key=value
      int eqPos = StringFind(line, "=");
      if(eqPos > 0)
      {
         string key = StringTrimLeft(StringTrimRight(StringSubstr(line, 0, eqPos)));
         string value = StringTrimLeft(StringTrimRight(StringSubstr(line, eqPos + 1)));
         
         if(key == "NumberOfCandles")
         {
            NumberOfCandles = (int)StringToInteger(value);
            Print("  NumberOfCandles = ", NumberOfCandles);
         }
         else if(key == "StopLossPoints")
         {
            StopLossPoints = StringToDouble(value);
            Print("  StopLossPoints = ", StopLossPoints);
         }
         else if(key == "TakeProfitPoints")
         {
            TakeProfitPoints = StringToDouble(value);
            Print("  TakeProfitPoints = ", TakeProfitPoints);
         }
      }
   }
   
   FileClose(fileHandle);
   Print("Settings file loaded successfully");
}

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   // Read settings from file (overrides input parameters)
   ReadSettingsFile();
   
   // Create directory if it doesn't exist
   if(!FolderCreate(FolderName, 0))
   {
      int error = GetLastError();
      if(error != 5018) // Error 5018 means folder already exists, which is OK
      {
         Print("Error creating folder: ", FolderName, " Error code: ", error);
      }
      else
      {
         Print("Folder already exists: ", FolderName);
      }
   }
   else
   {
      Print("Created folder: ", FolderName);
   }
   
   string trimmedPythonHome = StringTrimLeft(StringTrimRight(PythonHomePath));
   ScriptDirectory = StringTrimLeft(StringTrimRight(PythonScriptsDir));
   if(StringLen(ScriptDirectory) == 0)
   {
      if(MQLInfoInteger(MQL_TESTER) == 1)
         ScriptDirectory = TerminalInfoString(TERMINAL_DATA_PATH) + "\\tester\\files";
      else
         ScriptDirectory = TerminalInfoString(TERMINAL_DATA_PATH) + "\\MQL4\\Files";
   }

   int initResult = InitializePython(trimmedPythonHome, ScriptDirectory);
   if(initResult == 0)
   {
      Print("Failed to initialize Python analyzer DLL");
      return(INIT_FAILED);
   }

   if(StringLen(trimmedPythonHome) > 0)
      Print("Python home: ", trimmedPythonHome);
   else
      Print("Python home: <system default>");

   Print("Python scripts directory: ", ScriptDirectory);

   lastBarTime = iTime(Symbol(), PERIOD_M15, 0);
   Print("SaveM15Candles EA initialized. Monitoring M15 candles...");
   Print("Files will be saved to: MT4\\MQL4\\Files\\", FolderName);
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   FinalizePython();

   // Calculate trading statistics
   int totalTrades = 0;
   int winningTrades = 0;
   int losingTrades = 0;
   int buyTrades = 0;
   int sellTrades = 0;
   double totalProfit = 0.0;
   double totalLoss = 0.0;
   double grossProfit = 0.0;
   double grossLoss = 0.0;
   
   // Scan through open orders (may still be open during deinit in tester)
   int totalOpen = OrdersTotal();
   for(int i = 0; i < totalOpen; i++)
   {
      if(OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
      {
         if(OrderSymbol() == Symbol())
         {
            totalTrades++;
            // For open orders, calculate unrealized profit
            double profit = OrderProfit() + OrderSwap() + OrderCommission();
            
            if(profit > 0)
            {
               winningTrades++;
               grossProfit += profit;
            }
            else if(profit < 0)
            {
               losingTrades++;
               grossLoss += profit;
            }
            
            totalProfit += profit;
            
            if(OrderType() == OP_BUY)
               buyTrades++;
            else if(OrderType() == OP_SELL)
               sellTrades++;
         }
      }
   }
   
   // Scan through history
   int totalHistory = OrdersHistoryTotal();
   for(int i = 0; i < totalHistory; i++)
   {
      if(OrderSelect(i, SELECT_BY_POS, MODE_HISTORY))
      {
         if(OrderSymbol() == Symbol())
         {
            totalTrades++;
            double profit = OrderProfit() + OrderSwap() + OrderCommission();
            
            if(profit > 0)
            {
               winningTrades++;
               grossProfit += profit;
            }
            else if(profit < 0)
            {
               losingTrades++;
               grossLoss += profit;
            }
            
            totalProfit += profit;
            
            if(OrderType() == OP_BUY)
               buyTrades++;
            else if(OrderType() == OP_SELL)
               sellTrades++;
         }
      }
   }

   // Create a summary file with current date and time at end of testing
   datetime now = TimeCurrent();
   string filename = StringFormat("%s\\test_completed_%02d-%02d-%02d-%02d-%02d.txt",
                                   FolderName,
                                   TimeYear(now) % 100,
                                   TimeMonth(now),
                                   TimeDay(now),
                                   TimeHour(now),
                                   TimeMinute(now));
   
   int fileHandle = FileOpen(filename, FILE_WRITE|FILE_TXT);
   
   if(fileHandle != INVALID_HANDLE)
   {
      FileWrite(fileHandle, "========================================");
      FileWrite(fileHandle, "     TRADING RESULTS SUMMARY");
      FileWrite(fileHandle, "========================================");
      FileWrite(fileHandle, "");
      FileWrite(fileHandle, "Test Completed");
      FileWrite(fileHandle, "Date: ", TimeToString(now, TIME_DATE));
      FileWrite(fileHandle, "Time: ", TimeToString(now, TIME_MINUTES));
      FileWrite(fileHandle, "Symbol: ", Symbol());
      FileWrite(fileHandle, "Timeframe: M15");
      
      // Write last M15 candle time
      datetime lastCandle = iTime(Symbol(), PERIOD_M15, 0);
      FileWrite(fileHandle, "Last M15 Candle: ", TimeToString(lastCandle, TIME_DATE|TIME_MINUTES));
      
      FileWrite(fileHandle, "");
      FileWrite(fileHandle, "========================================");
      FileWrite(fileHandle, "     TRADING STATISTICS");
      FileWrite(fileHandle, "========================================");
      FileWrite(fileHandle, "Total Trades: ", totalTrades);
      FileWrite(fileHandle, "Winning Trades: ", winningTrades);
      FileWrite(fileHandle, "Losing Trades: ", losingTrades);
      FileWrite(fileHandle, "Buy Trades: ", buyTrades);
      FileWrite(fileHandle, "Sell Trades: ", sellTrades);
      FileWrite(fileHandle, "");
      FileWrite(fileHandle, "Win Rate: ", totalTrades > 0 ? DoubleToString((double)winningTrades / totalTrades * 100, 2) : "0.00", "%");
      FileWrite(fileHandle, "");
      FileWrite(fileHandle, "Gross Profit: ", DoubleToString(grossProfit, 2));
      FileWrite(fileHandle, "Gross Loss: ", DoubleToString(grossLoss, 2));
      FileWrite(fileHandle, "Net Profit: ", DoubleToString(totalProfit, 2));
      FileWrite(fileHandle, "Profit Factor: ", grossLoss != 0 ? DoubleToString(grossProfit / MathAbs(grossLoss), 2) : "N/A");
      FileWrite(fileHandle, "");
      FileWrite(fileHandle, "Initial Balance: ", DoubleToString(AccountBalance() - totalProfit, 2));
      FileWrite(fileHandle, "Final Balance: ", DoubleToString(AccountBalance(), 2));
      FileWrite(fileHandle, "========================================");
      
      FileClose(fileHandle);
      Print("Test completion file created: ", filename);
   }
   else
   {
      Print("Error creating test completion file. Error code: ", GetLastError());
   }
   
   // Print summary to terminal log
   Print("========================================");
   Print("TRADING RESULTS SUMMARY");
   Print("========================================");
   Print("Total Trades: ", totalTrades);
   Print("Winning Trades: ", winningTrades, " | Losing Trades: ", losingTrades);
   Print("Win Rate: ", totalTrades > 0 ? DoubleToString((double)winningTrades / totalTrades * 100, 2) : "0.00", "%");
   Print("Net Profit: ", DoubleToString(totalProfit, 2));
   Print("Final Balance: ", DoubleToString(AccountBalance(), 2));
   Print("========================================");
   
   Print("SaveM15Candles EA deinitialized. Reason: ", reason);
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   datetime currentBarTime = iTime(Symbol(), PERIOD_M15, 0);
   
   // Check if new M15 candle appeared
   if(currentBarTime != lastBarTime)
   {
      Print("New M15 candle detected at ", TimeToString(currentBarTime));
      string savedFile = SaveCandles();
      if(savedFile != "")
      {
         Print("Saved file: ", savedFile);
         
         // Analyze candles and decide order direction
         AnalyzeCandlesAndTrade(savedFile);
      }

      lastBarTime = currentBarTime;
   }
}

//+------------------------------------------------------------------+
//| Save last 10 candles to file                                     |
//+------------------------------------------------------------------+
string SaveCandles()
{
   int period = PERIOD_M15;
   string symbol = Symbol();
   
   // Get current time for filename
   datetime now = TimeCurrent();
   
   // Format: yy-mm-dd-hh-min
   string filename = StringFormat("%s\\%02d-%02d-%02d-%02d-%02d.csv",
                                   FolderName,
                                   TimeYear(now) % 100,
                                   TimeMonth(now),
                                   TimeDay(now),
                                   TimeHour(now),
                                   TimeMinute(now));
   
   // Check if file already exists
   if(FileIsExist(filename, 0))
   {
      Print("File already exists: ", filename, " - skipping save");
      return filename;
   }
   
   // Open file for writing
   int fileHandle = FileOpen(filename, FILE_WRITE|FILE_CSV);
   
   if(fileHandle == INVALID_HANDLE)
   {
      Print("Error opening file: ", filename, " Error code: ", GetLastError());
      return "";
   }
   
   // Write header
   FileWrite(fileHandle, "Time", "Open", "High", "Low", "Close", "Volume");
   
   // Write last N candles (from oldest to newest)
   int candlesToSave = NumberOfCandles;
   if(candlesToSave < 1) candlesToSave = 10;  // Default to 10 if invalid
   
   for(int i = candlesToSave - 1; i >= 0; i--)
   {
      datetime time = iTime(symbol, period, i);
      double open = iOpen(symbol, period, i);
      double high = iHigh(symbol, period, i);
      double low = iLow(symbol, period, i);
      double close = iClose(symbol, period, i);
      long volume = iVolume(symbol, period, i);
      
      FileWrite(fileHandle, 
                TimeToString(time, TIME_DATE|TIME_MINUTES),
                DoubleToString(open, Digits),
                DoubleToString(high, Digits),
                DoubleToString(low, Digits),
                DoubleToString(close, Digits),
                IntegerToString(volume));
   }
   
   FileClose(fileHandle);
   Print("Saved ", candlesToSave, " candles to: ", filename);
   return filename;
}

//+------------------------------------------------------------------+
//| Check if there are any open orders                                |
//+------------------------------------------------------------------+
bool HasOpenOrders()
{
   for(int i = 0; i < OrdersTotal(); i++)
   {
      if(OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
      {
         if(OrderSymbol() == Symbol())
         {
            string orderType = (OrderType() == OP_BUY) ? "BUY" : "SELL";
            double orderProfit = OrderProfit() + OrderSwap() + OrderCommission();
            Print("Has open order - Ticket: ", OrderTicket(), 
                  " | Type: ", orderType,
                  " | Lots: ", DoubleToString(OrderLots(), 2),
                  " | Entry: ", DoubleToString(OrderOpenPrice(), Digits),
                  " | Current: ", DoubleToString((OrderType() == OP_BUY) ? Bid : Ask, Digits),
                  " | Profit: ", DoubleToString(orderProfit, 2));
            return true;
         }
      }
   }
   return false;
}

//+------------------------------------------------------------------+
//| Analyze candles using Python script and decide trade direction   |
//+------------------------------------------------------------------+
void AnalyzeCandlesAndTrade(string csvFilename)
{
   // Check if we already have an open order
   if(HasOpenOrders())
   {
      Print("Order already open - skipping new trade signal");
      return;
   }
   
   string basePath = TerminalInfoString(TERMINAL_DATA_PATH);
   if(MQLInfoInteger(MQL_TESTER) == 1)
      basePath += "\\tester\\files\\";
   else
      basePath += "\\MQL4\\Files\\";

   string absoluteCsv = basePath + csvFilename;
   Print("Running DLL-based Python analysis for: ", absoluteCsv);

   int decision = AnalyzeCandles(absoluteCsv);
   if(decision == 1)
   {
      Print("DECISION from Python: More white candles - Opening BUY order");
      OpenBuyOrder();
   }
   else if(decision == -1)
   {
      Print("DECISION from Python: More black candles - Opening SELL order");
      OpenSellOrder();
   }
   else
   {
      Print("ERROR: Python analyzer returned invalid signal - skipping trade");
   }
}

//+------------------------------------------------------------------+
//| Open a Buy order                                                  |
//+------------------------------------------------------------------+
void OpenBuyOrder()
{
   double lotSize = 0.01;  // Minimum lot size
   double price = Ask;
   
   // Get minimum stop level required by broker
   double minStopLevel = MarketInfo(Symbol(), MODE_STOPLEVEL) * Point;
   
   // Calculate SL and TP based on input parameters
   double sl = 0;
   double tp = 0;
   
   if(StopLossPoints > 0)
   {
      double slDistance = StopLossPoints * Point;
      // Ensure minimum distance
      if(minStopLevel > 0 && slDistance < minStopLevel)
         slDistance = minStopLevel * 1.5;  // Use 1.5x minimum if too small
      sl = NormalizeDouble(price - slDistance, Digits);
   }
   
   if(TakeProfitPoints > 0)
   {
      double tpDistance = TakeProfitPoints * Point;
      // Ensure minimum distance
      if(minStopLevel > 0 && tpDistance < minStopLevel)
         tpDistance = minStopLevel * 1.5;  // Use 1.5x minimum if too small
      tp = NormalizeDouble(price + tpDistance, Digits);
   }
   
   Print("Attempting BUY order: Price=", price, " SL=", sl, " TP=", tp, " MinStopLevel=", minStopLevel);
   
   int ticket = OrderSend(Symbol(), OP_BUY, lotSize, price, 3, sl, tp, "Buy from analysis", 0, 0, clrGreen);
   
   if(ticket > 0)
   {
      Print("BUY order opened successfully. Ticket: ", ticket, " | Entry: ", price, " | SL: ", sl, " | TP: ", tp);
   }
   else
   {
      Print("Error opening BUY order. Error code: ", GetLastError(), " | MinStopLevel: ", minStopLevel);
   }
}

//+------------------------------------------------------------------+
//| Open a Sell order                                                 |
//+------------------------------------------------------------------+
void OpenSellOrder()
{
   double lotSize = 0.01;  // Minimum lot size
   double price = Bid;
   
   // Get minimum stop level required by broker
   double minStopLevel = MarketInfo(Symbol(), MODE_STOPLEVEL) * Point;
   
   // Calculate SL and TP based on input parameters
   double sl = 0;
   double tp = 0;
   
   if(StopLossPoints > 0)
   {
      double slDistance = StopLossPoints * Point;
      // Ensure minimum distance
      if(minStopLevel > 0 && slDistance < minStopLevel)
         slDistance = minStopLevel * 1.5;  // Use 1.5x minimum if too small
      sl = NormalizeDouble(price + slDistance, Digits);
   }
   
   if(TakeProfitPoints > 0)
   {
      double tpDistance = TakeProfitPoints * Point;
      // Ensure minimum distance
      if(minStopLevel > 0 && tpDistance < minStopLevel)
         tpDistance = minStopLevel * 1.5;  // Use 1.5x minimum if too small
      tp = NormalizeDouble(price - tpDistance, Digits);
   }
   
   Print("Attempting SELL order: Price=", price, " SL=", sl, " TP=", tp, " MinStopLevel=", minStopLevel);
   
   int ticket = OrderSend(Symbol(), OP_SELL, lotSize, price, 3, sl, tp, "Sell from analysis", 0, 0, clrRed);
   
   if(ticket > 0)
   {
      Print("SELL order opened successfully. Ticket: ", ticket, " | Entry: ", price, " | SL: ", sl, " | TP: ", tp);
   }
   else
   {
      Print("Error opening SELL order. Error code: ", GetLastError(), " | MinStopLevel: ", minStopLevel);
   }
}
//+------------------------------------------------------------------+
