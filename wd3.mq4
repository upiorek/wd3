//+------------------------------------------------------------------+
//|                                                         WD3.mq4 |
//|                                          Simplified Expert v3.5 |
//+------------------------------------------------------------------+

// Global variables
datetime lastLogTime = 0;
datetime lastFileCheck = 0;
int hearbeat = 0;
string version = "3.5";
void LogAccountInfo()
{
   int fileHandle = FileOpen("account_log.txt", FILE_WRITE|FILE_TXT);
   
   if(fileHandle != INVALID_HANDLE)
   {
      string logData = "WD: " + version + " | " + 
                      TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS) + " | " +
                      "Account: " + IntegerToString(AccountNumber()) + " | " +
                      "Balance: " + DoubleToString(AccountBalance(), 2) + " | " +
                      "Equity: " + DoubleToString(AccountEquity(), 2) + " | " +
                      "Profit: " + DoubleToString(AccountProfit(), 2) + " | " +
                      "Margin: " + DoubleToString(AccountMargin(), 2) + " | " +
                      "Free Margin: " + DoubleToString(AccountFreeMargin(), 2) + " | " +
                      "Margin Level: " + DoubleToString(AccountMargin() > 0 ? (AccountEquity() / AccountMargin()) * 100 : 0, 2) + "% | " +
                      "Orders: " + IntegerToString(OrdersTotal()) + " | " +
                      "Heartbeat: " + IntegerToString(hearbeat) + "\n";
      
      FileSeek(fileHandle, 0, SEEK_END);
      FileWriteString(fileHandle, logData);
      FileClose(fileHandle);
      
      Print("WD: " + version + " heartbeat: " + hearbeat);
   }
   else
   {
      Print("Error opening log file: ", GetLastError());
   }
}

//+------------------------------------------------------------------+
//| Read and process order from approved.txt file                       |
//+------------------------------------------------------------------+
void ReadAndSendOrderFromFile()
{
   int fileHandle = FileOpen("approved.txt", FILE_READ|FILE_TXT);
   
   if(fileHandle != INVALID_HANDLE)
   {
      string fileContent = "";
      while(!FileIsEnding(fileHandle))
      {
         string line = FileReadString(fileHandle);
         if(line != "") fileContent += line + "\n";
      }
      FileClose(fileHandle);
      
      if(fileContent != "") ParseAndSendOrder(fileContent);
   }
}

//+------------------------------------------------------------------+
//| Parse order data and send order (Space-separated format only)   |
//| Format: SYMBOL TYPE LOTS PRICE STOPLOSS TAKEPROFIT              |
//+------------------------------------------------------------------+
void ParseAndSendOrder(string orderData)
{
   string lines[];
   int linesCount = StringSplit(orderData, '\n', lines);
   
   for(int i = 0; i < linesCount; i++)
   {
      string line = StringTrimLeft(StringTrimRight(lines[i]));
      if(line == "" || StringFind(line, "#") == 0) continue;
      
      string parts[];
      int partsCount = StringSplit(line, ' ', parts);
      
      if(partsCount >= 6)
      {
         string symbol = parts[0];
         int orderType = GetOrderType(parts[1]);
         double lots = StringToDouble(parts[2]);
         double price = StringToDouble(parts[3]);
         double stopLoss = StringToDouble(parts[4]);
         double takeProfit = StringToDouble(parts[5]);
         
         if(symbol != "" && lots > 0 && orderType >= 0)
         {
            if((orderType == OP_BUY || orderType == OP_SELL) && price == 0.0)
            {
               price = (orderType == OP_BUY) ? MarketInfo(symbol, MODE_ASK) : MarketInfo(symbol, MODE_BID);
            }
            
            int ticket = OrderSend(symbol, orderType, lots, price, 3, stopLoss, takeProfit, "wd", 0, 0, clrNONE);
            
            if(ticket > 0)
            {
               Print("Order sent successfully! Ticket: ", ticket, " Symbol: ", symbol);
               ClearApprovedFile();
            }
            else
            {
               Print("Error sending order: ", GetLastError());
            }
         }
      }
   }
}

int GetOrderType(string typeStr)
{
   if(typeStr == "BUY") return OP_BUY;
   if(typeStr == "SELL") return OP_SELL;
   if(typeStr == "BUYLIMIT") return OP_BUYLIMIT;
   if(typeStr == "SELLLIMIT") return OP_SELLLIMIT;
   if(typeStr == "BUYSTOP") return OP_BUYSTOP;
   if(typeStr == "SELLSTOP") return OP_SELLSTOP;
   return -1;
}

void ClearApprovedFile()
{
   int fileHandle = FileOpen("approved.txt", FILE_WRITE|FILE_TXT);
   if(fileHandle != INVALID_HANDLE)
   {
      string clearMessage = "\n";
      FileWriteString(fileHandle, clearMessage);
      FileClose(fileHandle);
   }
}

void LogAllOrders()
{
   int fileHandle = FileOpen("orders_log.txt", FILE_WRITE|FILE_TXT);
   
   if(fileHandle != INVALID_HANDLE)
   {
      string logData = "=== ORDERS LOG " + TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS) + " ===\n";
      logData += "Total Orders: " + IntegerToString(OrdersTotal()) + "\n";
      
      if(OrdersTotal() > 0)
      {
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
               }
               
               logData += IntegerToString(OrderTicket()) + " | " + orderType + " | " + OrderSymbol() + " | " +
                         DoubleToString(OrderLots(), 2) + " | " + DoubleToString(OrderOpenPrice(), 5) + " | " +
                         DoubleToString(OrderStopLoss(), 5) + " | " + DoubleToString(OrderTakeProfit(), 5) + " | " +
                         DoubleToString(OrderProfit(), 2) + "\n";
            }
         }
      }
      else
      {
         logData += "No open orders\n";
      }
      
      logData += "=== END LOG ===\n\n";
      
      FileSeek(fileHandle, 0, SEEK_END);
      FileWriteString(fileHandle, logData);
      FileClose(fileHandle);
   }
}

void OnTick()
{
   datetime currentTime = TimeCurrent();
   hearbeat++;
   
   // Log account info every 10 seconds
   if(currentTime - lastLogTime >= 10)
   {
      LogAccountInfo();
      LogAllOrders();
      lastLogTime = currentTime;
   }
   
   // Check for file orders every 5 seconds
   if(currentTime - lastFileCheck >= 15)
   {
      ReadAndSendOrderFromFile();
      lastFileCheck = currentTime;
   }
}
