//+------------------------------------------------------------------+
//|                                                  MACD Sample.mq4 |
//|                             Copyright 2000-2025, MetaQuotes Ltd. |
//|                                              http://www.mql5.com |
//+------------------------------------------------------------------+

// Variables for account logging
datetime lastLogTime = 0;
int logInterval = 10; // seconds
string logFilePath = "account_log.txt";
int hearbeat = 0;
int wd3verMax = 3;
int wd3verMin = 3;
//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
void LogAccountInfo()
  {
   int fileHandle;
   string logData;
   
   // Try to create directory if it doesn't exist (for Files folder)
   // This is only needed if using subdirectories
   
   // Open file for writing (append mode)
   fileHandle = FileOpen(logFilePath, FILE_WRITE|FILE_TXT);
   
   if(fileHandle != INVALID_HANDLE)
     {
      // Prepare account information
      logData += "WD: " + wd3verMax + "." + wd3verMin + "\n";
      logData += TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS) + " | ";
      logData += "Account: " + IntegerToString(AccountNumber()) + " | ";
      logData += "Balance: " + DoubleToString(AccountBalance(), 2) + " | ";
      logData += "Equity: " + DoubleToString(AccountEquity(), 2) + " | ";
      logData += "Free Margin: " + DoubleToString(AccountFreeMargin(), 2) + " | ";
      logData += "Margin: " + DoubleToString(AccountMargin(), 2) + " | ";
      logData += "Margin Level: " + DoubleToString(AccountMargin() > 0 ? AccountEquity()/AccountMargin()*100 : 0, 2) + "% | ";
      logData += "Profit: " + DoubleToString(AccountProfit(), 2) + " | ";
      logData += "Currency: " + AccountCurrency() + " | ";
      logData += "Leverage: 1:" + IntegerToString(AccountLeverage()) + " | ";
      logData += "Orders: " + IntegerToString(OrdersTotal());
      logData += "\n";
      logData += "hearbeat: " + hearbeat;

      Print("WD: " + wd3verMax + "." + wd3verMin + " hearbeat: " + hearbeat);
      
      // Seek to end of file and write data
      FileSeek(fileHandle, 0, SEEK_END);
      FileWriteString(fileHandle, logData + "\n");
      FileClose(fileHandle);
      
      Print("Account info logged to file, hearbeat: " + hearbeat);
     }
   else
     {
      int error = GetLastError();
      Print("Error opening log file: ", error);
      Print("Attempted file path: ", logFilePath);
     }
  }

//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
void OnTick(void)
  {
   // Log account info every 10 seconds
   datetime currentTime = TimeCurrent();
   hearbeat++;
   if(currentTime - lastLogTime >= logInterval)
     {
      LogAccountInfo();
      lastLogTime = currentTime;
     }
  }
//+------------------------------------------------------------------+
