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
//| Function to log all current orders                              |
//+------------------------------------------------------------------+
void LogAllOrders()
  {
   int fileHandle;
   string logData = "";
   string orderLogPath = "orders_log.txt";
   
   // Open file for writing (append mode)
   fileHandle = FileOpen(orderLogPath, FILE_WRITE|FILE_TXT);
   
   if(fileHandle != INVALID_HANDLE)
     {
      // Log header with timestamp
      logData += "=== ORDERS LOG " + TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS) + " ===\n";
      logData += "Total Orders: " + IntegerToString(OrdersTotal()) + "\n";
      
      if(OrdersTotal() > 0)
        {
         logData += "Ticket | Type | Symbol | Lots | OpenPrice | StopLoss | TakeProfit | Profit | Comment\n";
         logData += "-------|------|--------|------|-----------|----------|------------|--------|--------\n";
         
         // Loop through all orders
         for(int i = 0; i < OrdersTotal(); i++)
           {
            if(OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
              {
               string orderType = "";
               switch(OrderType())
                 {
                  case OP_BUY: orderType = "BUY"; break;
                  case OP_SELL: orderType = "SELL"; break;
                  case OP_BUYLIMIT: orderType = "BUY LIMIT"; break;
                  case OP_SELLLIMIT: orderType = "SELL LIMIT"; break;
                  case OP_BUYSTOP: orderType = "BUY STOP"; break;
                  case OP_SELLSTOP: orderType = "SELL STOP"; break;
                  default: orderType = "UNKNOWN"; break;
                 }
               
               logData += IntegerToString(OrderTicket()) + " | ";
               logData += orderType + " | ";
               logData += OrderSymbol() + " | ";
               logData += DoubleToString(OrderLots(), 2) + " | ";
               logData += DoubleToString(OrderOpenPrice(), Digits) + " | ";
               logData += DoubleToString(OrderStopLoss(), Digits) + " | ";
               logData += DoubleToString(OrderTakeProfit(), Digits) + " | ";
               logData += DoubleToString(OrderProfit(), 2) + " | ";
               logData += OrderComment() + "\n";
              }
            else
              {
               Print("Error selecting order at position ", i, ": ", GetLastError());
              }
           }
        }
      else
        {
         logData += "No open orders\n";
        }
      
      logData += "=== END ORDERS LOG ===\n\n";
      
      // Seek to end of file and write data
      FileSeek(fileHandle, 0, SEEK_END);
      FileWriteString(fileHandle, logData);
      FileClose(fileHandle);
      
      Print("Orders logged to file: ", orderLogPath);
     }
   else
     {
      int error = GetLastError();
      Print("Error opening orders log file: ", error);
      Print("Attempted file path: ", orderLogPath);
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
      LogAllOrders();
      lastLogTime = currentTime;
     }
  }
//+------------------------------------------------------------------+
