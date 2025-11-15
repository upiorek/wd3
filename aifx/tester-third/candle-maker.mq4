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
string version = "3.01";

datetime lastBarTime = 0;
int    NumberOfCandles    = 10;

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
//| Save last NumberOfCandles candles to file                                     |
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
   if(candlesToSave < 1) candlesToSave = NumberOfCandles;  // Default to 10 if invalid
   
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
