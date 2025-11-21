//+------------------------------------------------------------------+
//|                                              SaveM15Candles.mq4  |
//|                                                                  |
//|  Saves last n M15 candles to file on each new candle             |
//+------------------------------------------------------------------+
#property copyright "Copyright 2025"
#property link      ""
#property strict

// Specify subdirectory name (will be created in MT4 Files folder)
string FolderName = "m15_candles";
string version = "3.06";

datetime lastBarTime = 0;
int HistoryBefore = 100;   // Candles before the named candle
int CandlesAfter = 19;    // Candles after the named candle

// Decision tracking (matching order-maker logic)
bool decisionMade = false;
string pendingOrderType = "";
datetime decisionTime = 0;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{   
   Print("version: " + version);
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

   // Initialize lastBarTime to 0 so first OnTick is always treated as new candle
   lastBarTime = 0;
   Print("SaveM15Candles EA initialized. Monitoring M15 candles...");
   Print("Files will be saved to: MT4\\MQL4\\Files\\", FolderName);
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
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
      }

      lastBarTime = currentBarTime;
   }
}

//+------------------------------------------------------------------+
//| Save candles with filename in the middle of the range            |
//+------------------------------------------------------------------+
string SaveCandles()
{
   int period = PERIOD_M15;
   string symbol = Symbol();
   
   // Get time for the MIDDLE candle (bar[10])
   // Current bar is bar[0], we want to name file after bar[10] (10 candles ago)
   datetime middleTime = iTime(symbol, period, CandlesAfter);
   
   // Format: yy-mm-dd-hh-min
   string filename = StringFormat("%s\\%02d-%02d-%02d-%02d-%02d.csv",
                                   FolderName,
                                   TimeYear(middleTime) % 100,
                                   TimeMonth(middleTime),
                                   TimeDay(middleTime),
                                   TimeHour(middleTime),
                                   TimeMinute(middleTime));
   
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
   FileWrite(fileHandle, "Time", "Open", "High", "Low", "Close");
   
   // Write candles: HistoryBefore candles before middle + middle candle + CandlesAfter candles after middle
   // Start from bar[HistoryBefore + CandlesAfter] and go to bar[0]
   // Example: 10 before + 10 after = start from bar[20] to bar[0] = 21 candles total
   int startBar = HistoryBefore + CandlesAfter;
   
   for(int i = startBar; i >= 0; i--)
   {
      datetime time = iTime(symbol, period, i);
      double open = iOpen(symbol, period, i);
      double high = iHigh(symbol, period, i);
      double low = iLow(symbol, period, i);
      double close = iClose(symbol, period, i);
      
      FileWrite(fileHandle, 
                TimeToString(time, TIME_DATE|TIME_MINUTES),
                DoubleToString(open, Digits),
                DoubleToString(high, Digits),
                DoubleToString(low, Digits),
                DoubleToString(close, Digits));
   }
   
   FileClose(fileHandle);
   Print("Saved ", startBar + 1, " candles (bar[", startBar, "] to bar[0]) with middle at bar[", CandlesAfter, "] to: ", filename);
   return filename;
}
