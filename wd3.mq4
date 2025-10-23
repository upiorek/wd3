//+------------------------------------------------------------------+
//|                                                         WD3.mq4 |
//+------------------------------------------------------------------+

// Global variables
datetime lastLogTime = 0;
datetime lastFileCheck = 0;
datetime lastHistoryLogTime = 0;
datetime lastDroppedCheck = 0;
datetime lastModifiedCheck = 0;
datetime lastMarketLogTime = 0;
int hearbeat = 0;
string version = "3.11";
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
   }
   else
   {
      Print("Error opening log file: ", GetLastError());
   }
}

void LogMarketData()
{
   int fileHandle = FileOpen("market_log.txt", FILE_WRITE|FILE_TXT);
   
   if(fileHandle != INVALID_HANDLE)
   {
      // Get current prices for US100.f and EURUSD
      double us100Bid = MarketInfo("US100.f", MODE_BID);
      double us100Ask = MarketInfo("US100.f", MODE_ASK);
      double us100 = (us100Bid + us100Ask) / 2;
      double eurusdBid = MarketInfo("EURUSD", MODE_BID);
      double eurusdAsk = MarketInfo("EURUSD", MODE_ASK);
      double eurusd = (eurusdBid + eurusdAsk) / 2;
      
      string logData = "WD: " + version + " | " + 
                      TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS) + " | " +
                      "US100.f: " + DoubleToString(us100, 2) + " | " +
                      "EURUSD: " + DoubleToString(eurusd, 5) + " | " +
                      "Heartbeat: " + IntegerToString(hearbeat) + "\n";
      
      FileSeek(fileHandle, 0, SEEK_END);
      FileWriteString(fileHandle, logData);
      FileClose(fileHandle);
   }
   else
   {
      Print("Error opening market log file: ", GetLastError());
   }
}

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

void ClearModifiedFile()
{
   int fileHandle = FileOpen("modified.txt", FILE_WRITE|FILE_TXT);
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

void CheckAndCancelDroppedOrders()
{
   int fileHandle = FileOpen("dropped.txt", FILE_READ|FILE_TXT);
   
   if(fileHandle != INVALID_HANDLE)
   {
      string ticketsToCancel[];
      string remainingTickets[];
      int cancelCount = 0;
      int remainingCount = 0;
      
      // Read all tickets from dropped.txt
      while(!FileIsEnding(fileHandle))
      {
         string line = FileReadString(fileHandle);
         line = StringTrimLeft(StringTrimRight(line));
         if(line != "")
         {
            int ticket = StringToInteger(line);
            if(ticket > 0)
            {
               // Check if this ticket is an open order
               bool orderFound = false;
               for(int i = 0; i < OrdersTotal(); i++)
               {
                  if(OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
                  {
                     if(OrderTicket() == ticket)
                     {
                        orderFound = true;
                        break;
                     }
                  }
               }
               
               if(orderFound)
               {
                  // Add to cancel list
                  ArrayResize(ticketsToCancel, cancelCount + 1);
                  ticketsToCancel[cancelCount] = line;
                  cancelCount++;
               }
               else
               {
                  // Keep in file (order not found or already closed)
                  ArrayResize(remainingTickets, remainingCount + 1);
                  remainingTickets[remainingCount] = line;
                  remainingCount++;
               }
            }
         }
      }
      FileClose(fileHandle);
      
      // Cancel the found orders
      for(int j = 0; j < cancelCount; j++)
      {
         int ticketToCancel = StringToInteger(ticketsToCancel[j]);
         if(OrderSelect(ticketToCancel, SELECT_BY_TICKET))
         {
            bool closed = false;
            if(OrderType() == OP_BUY)
            {
               closed = OrderClose(ticketToCancel, OrderLots(), MarketInfo(OrderSymbol(), MODE_BID), 3, clrRed);
            }
            else if(OrderType() == OP_SELL)
            {
               closed = OrderClose(ticketToCancel, OrderLots(), MarketInfo(OrderSymbol(), MODE_ASK), 3, clrRed);
            }
            else
            {
               // For pending orders
               closed = OrderDelete(ticketToCancel);
            }
            
            if(closed)
            {
               Print("Successfully cancelled order: ", ticketToCancel);
            }
            else
            {
               Print("Failed to cancel order: ", ticketToCancel, " Error: ", GetLastError());
               // If failed to cancel, keep the ticket in the file
               ArrayResize(remainingTickets, remainingCount + 1);
               remainingTickets[remainingCount] = ticketsToCancel[j];
               remainingCount++;
            }
         }
      }
      
      // Rewrite dropped.txt with only remaining tickets
      int writeHandle = FileOpen("dropped.txt", FILE_WRITE|FILE_TXT);
      if(writeHandle != INVALID_HANDLE)
      {
         for(int k = 0; k < remainingCount; k++)
         {
            FileWriteString(writeHandle, remainingTickets[k] + "\n");
         }
         FileClose(writeHandle);
      }
   }
}

void LogOrderHistory()
{
   int fileHandle = FileOpen("order_history_log.txt", FILE_WRITE|FILE_TXT);
   
   if(fileHandle != INVALID_HANDLE)
   {
      datetime currentDay = StringToTime(TimeToString(TimeCurrent(), TIME_DATE));
      datetime nextDay = currentDay + 86400; // Add 24 hours
      
      string logData = "=== ORDER HISTORY LOG " + TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS) + " ===\n";
      logData += "Current Day Orders History\n";
      
      int totalHistoryOrders = OrdersHistoryTotal();
      int todayOrdersCount = 0;
      double totalProfit = 0.0;
      double totalCommission = 0.0;
      double totalNetProfit = 0.0;
      int winningOrders = 0;
      int losingOrders = 0;
      
      for(int i = 0; i < totalHistoryOrders; i++)
      {
         if(OrderSelect(i, SELECT_BY_POS, MODE_HISTORY))
         {
            datetime orderCloseTime = OrderCloseTime();
            
            // Check if order was closed today and is BUY or SELL order only
            if(orderCloseTime >= currentDay && orderCloseTime < nextDay && 
               (OrderType() == OP_BUY || OrderType() == OP_SELL))
            {
               todayOrdersCount++;
               double orderProfit = OrderProfit();
               double orderCommission = OrderCommission();
               double netProfit = orderProfit + orderCommission;
               
               totalProfit += orderProfit;
               totalCommission += orderCommission;
               totalNetProfit += netProfit;
               
               if(netProfit > 0) winningOrders++;
               else if(netProfit < 0) losingOrders++;
               
               string orderType = "";
               switch(OrderType())
               {
                  case OP_BUY: orderType = "BUY"; break;
                  case OP_SELL: orderType = "SELL"; break;
               }
               
               logData += IntegerToString(OrderTicket()) + " | " + orderType + " | " + OrderSymbol() + " | " +
                         DoubleToString(OrderLots(), 2) + " | " +
                         "Profit: " + DoubleToString(orderProfit, 2) + " | " +
                         "Commission: " + DoubleToString(orderCommission, 2) + " | " +
                         "Net: " + DoubleToString(netProfit, 2) + "\n";
            }
         }
      }
      
      if(todayOrdersCount == 0)
      {
         logData += "No orders closed today\n";
      }
      else
      {
         logData += "=== SUMMARY ===\n";
         logData += "Total orders closed today: " + IntegerToString(todayOrdersCount) + "\n";
         logData += "Total profit: " + DoubleToString(totalProfit, 2) + "\n";
         logData += "Total commission: " + DoubleToString(totalCommission, 2) + "\n";
         logData += "Total net profit: " + DoubleToString(totalNetProfit, 2) + "\n";
         logData += "Winning orders: " + IntegerToString(winningOrders) + "\n";
         logData += "Losing orders: " + IntegerToString(losingOrders) + "\n";
         if(todayOrdersCount > 0)
         {
            double winRate = (double)winningOrders / todayOrdersCount * 100.0;
            logData += "Win rate: " + DoubleToString(winRate, 1) + "%\n";
         }
      }
      
      logData += "=== END HISTORY LOG ===\n\n";
      
      FileSeek(fileHandle, 0, SEEK_END);
      FileWriteString(fileHandle, logData);
      FileClose(fileHandle);
   }
   else
   {
      Print("Error opening order history log file: ", GetLastError());
   }
}

void CheckAndModifyOrders()
{
   int fileHandle = FileOpen("modified.txt", FILE_READ|FILE_TXT);
   
   if(fileHandle != INVALID_HANDLE)
   {
      string remainingLines[];
      int modificationCount = 0;
      int remainingCount = 0;
      
      // Read all modification requests from modified.txt
      while(!FileIsEnding(fileHandle))
      {
         string line = FileReadString(fileHandle);
         line = StringTrimLeft(StringTrimRight(line));
         if(line != "" && StringFind(line, "#") != 0)
         {
            // Parse the modification line
            // Expected format: TICKET STOPLOSS TAKEPROFIT
            // Example: 12345 1.2500 1.3000
            string parts[];
            int partsCount = StringSplit(line, ' ', parts);
            
            if(partsCount >= 3)
            {
               int ticket = StringToInteger(parts[0]);
               double newStopLoss = StringToDouble(parts[1]);
               double newTakeProfit = StringToDouble(parts[2]);
               
               if(ticket > 0)
               {
                  // Try to modify the order
                  bool orderFound = false;
                  if(OrderSelect(ticket, SELECT_BY_TICKET))
                  {
                     orderFound = true;
                     
                     // Get current order information
                     double currentPrice = OrderOpenPrice();
                     
                     // For market orders, we need current market price for validation
                     if(OrderType() == OP_BUY || OrderType() == OP_SELL)
                     {
                        currentPrice = (OrderType() == OP_BUY) ? MarketInfo(OrderSymbol(), MODE_BID) : MarketInfo(OrderSymbol(), MODE_ASK);
                     }
                     
                     // Use current values if new values are 0
                     if(newStopLoss == 0.0) newStopLoss = OrderStopLoss();
                     if(newTakeProfit == 0.0) newTakeProfit = OrderTakeProfit();
                     
                     // Attempt to modify the order
                     bool modified = OrderModify(ticket, OrderOpenPrice(), newStopLoss, newTakeProfit, OrderExpiration(), clrNONE);
                     
                     if(modified)
                     {
                        Print("Successfully modified order: ", ticket, 
                              " SL: ", DoubleToString(newStopLoss, 5), 
                              " TP: ", DoubleToString(newTakeProfit, 5));
                     }
                     else
                     {
                        Print("Failed to modify order: ", ticket, " Error: ", GetLastError());
                        // If failed to modify, keep the line in the file for retry
                        ArrayResize(remainingLines, remainingCount + 1);
                        remainingLines[remainingCount] = line;
                        remainingCount++;
                     }
                  }
                  else
                  {
                     Print("Order not found for modification: ", ticket);
                     // Order not found, remove from file (might be closed)
                  }
               }
               else
               {
                  Print("Invalid ticket number in modified.txt: ", parts[0]);
                  // Invalid ticket, remove from file
               }
            }
            else
            {
               Print("Invalid format in modified.txt line: ", line);
               Print("Expected format: TICKET STOPLOSS TAKEPROFIT");
               // Invalid format, keep in file for manual review
               ArrayResize(remainingLines, remainingCount + 1);
               remainingLines[remainingCount] = line;
               remainingCount++;
            }
         }
      }
      FileClose(fileHandle);
      
      // Rewrite modified.txt with only remaining lines (failed modifications)
      int writeHandle = FileOpen("modified.txt", FILE_WRITE|FILE_TXT);
      if(writeHandle != INVALID_HANDLE)
      {
         for(int k = 0; k < remainingCount; k++)
         {
            FileWriteString(writeHandle, remainingLines[k] + "\n");
         }
         FileClose(writeHandle);
      }
   }
}

void OnTick()
{
   datetime currentTime = TimeCurrent();
   hearbeat++;
   
   // Log account info
   if(currentTime - lastLogTime >= 1)
   {
      LogAccountInfo();
      LogAllOrders();
      lastLogTime = currentTime;
   }
   
   // Log market data
   if(currentTime - lastMarketLogTime >= 1)
   {
      LogMarketData();
      lastMarketLogTime = currentTime;
   }
   
   // Log order history
   if(currentTime - lastHistoryLogTime >= 1)
   {
      LogOrderHistory();
      lastHistoryLogTime = currentTime;
   }
   
   // Check for dropped orders
   if(currentTime - lastDroppedCheck >= 1)
   {
      CheckAndCancelDroppedOrders();
      lastDroppedCheck = currentTime;
   }
   
   // Check for orders to modify
   if(currentTime - lastModifiedCheck >= 1)
   {
      CheckAndModifyOrders();
      lastModifiedCheck = currentTime;
   }
   
   // Check for orders
   if(currentTime - lastFileCheck >= 5)
   {
      ReadAndSendOrderFromFile();
      lastFileCheck = currentTime;
   }

   if(currentTime - lastFileCheck >= 30)
   {
      Print("WD: " + version + " heartbeat: " + hearbeat);
   }
}
