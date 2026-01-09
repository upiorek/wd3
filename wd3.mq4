//+------------------------------------------------------------------+
//|                                                         WD3.mq4 |
//+------------------------------------------------------------------+

//#include "wd_main.mqh"

// Global variables
datetime lastLogTime = 0;
datetime lastFileCheck = 0;
datetime lastHistoryLogTime = 0;
datetime lastDroppedCheck = 0;
datetime lastModifiedCheck = 0;
datetime lastMarketLogTime = 0;
datetime lastM1CandleTime = 0;
datetime lastM15CandleTime = 0;

int hearbeat = 0;
string version = "3.4";

// Simple risk management (read from wdsettings file)
double tp = 200;
double be = 100;
double sl = 50;
double bonus = 20;

bool settingsLoaded = false;

//-----------------------------------------------------------------------

void ReadSettings()
{
   int fileHandle = FileOpen("wdsettings", FILE_READ|FILE_TXT);
   
   if(fileHandle != INVALID_HANDLE)
   {
      while(!FileIsEnding(fileHandle))
      {
         string line = FileReadString(fileHandle);
         line = StringTrimLeft(StringTrimRight(line));
         
         // Skip empty lines and comments
         if(line == "" || StringFind(line, "//") == 0 || StringFind(line, "#") == 0)
            continue;
         
         // Parse key: value format
         int colonPos = StringFind(line, ":");
         if(colonPos > 0)
         {
            string key = StringTrimLeft(StringTrimRight(StringSubstr(line, 0, colonPos)));
            string value = StringTrimLeft(StringTrimRight(StringSubstr(line, colonPos + 1)));
            
            if(key == "tp")
               tp = StringToDouble(value);
            else if(key == "be")
               be = StringToDouble(value);
            else if(key == "sl")
               sl = StringToDouble(value);
            else if(key == "bonus")
               bonus = StringToDouble(value);
         }
      }
      FileClose(fileHandle);
      settingsLoaded = true;
      Print("Settings loaded from wdsettings: tp=", tp, " be=", be, " sl=", sl, " bonus=", bonus);
   }
   else
   {
      Print("Warning: Could not open wdsettings file, using default values");
      settingsLoaded = true; // Don't keep trying
   }
}

void LogAccountInfo()
{
   int fileHandle = FileOpen("account_log.txt", FILE_WRITE|FILE_TXT);
   
   if(fileHandle != INVALID_HANDLE)
   {
      string logData = "WD: " + version + " " + "Heartbeat: " + IntegerToString(hearbeat) + " / " + TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS) + " | " +
                      "Balance: " + DoubleToString(AccountBalance(), 2) + " / Equity: " + DoubleToString(AccountEquity(), 2) + " | " +
                      "Margin: " + DoubleToString(AccountMargin(), 2) + " / Free Margin: " + DoubleToString(AccountFreeMargin(), 2) + " | " +
                      "Margin Level: " + DoubleToString(AccountMargin() > 0 ? (AccountEquity() / AccountMargin()) * 100 : 0, 2) + "% | " +
                      "\n" + 
                      "Current Profit: " + DoubleToString(AccountProfit(), 2) + " | " +
                      "Active Orders: " + IntegerToString(OrdersTotal()) +
                      "\n" + 
                      "sl: " + DoubleToString(sl, 0) + " / be: " + DoubleToString(be, 0) + " / tp: " + DoubleToString(tp, 0) + " / bonus: " + DoubleToString(bonus, 0) + "\n";

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

      string logData = "Market:" + "\n" +
                       "US100.f: " + DoubleToString(us100, 2) + " | " +
                       "EURUSD: " + DoubleToString(eurusd, 5) + "\n";

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
            
            // Calculate SL and TP based on globals if not provided
            if((orderType == OP_BUY || orderType == OP_SELL) && stopLoss == 0.0 && takeProfit == 0.0)
            {
               if(orderType == OP_BUY)
               {
                  stopLoss = price - sl;
                  takeProfit = price + tp;
               }
               else if(orderType == OP_SELL)
               {
                  stopLoss = price + sl;
                  takeProfit = price - tp;
               }
               Print("Using calculated SL/TP - SL: ", DoubleToString(stopLoss, 2), " TP: ", DoubleToString(takeProfit, 2));
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
                         DoubleToString(OrderProfit(), 2) + " | " + TimeToString(OrderOpenTime(), TIME_DATE|TIME_SECONDS) + "\n";
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
      
      string logData = "history for: " + TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS) + "\n\n";
    
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
               
               logData += IntegerToString(OrderTicket()) + " | " + TimeToString(OrderOpenTime()) + " => " + TimeToString(OrderCloseTime()) + "\n" +
	                 orderType + " | " + OrderSymbol() + " | " + DoubleToString(OrderLots(), 2)  + "\n" +
                         "Open: " + DoubleToString(OrderOpenPrice(), 2) + " | " + "Profit: " + DoubleToString(orderProfit, 2) +
                         "\n---\n";
                         //"Commission: " + DoubleToString(orderCommission, 2)
                         //"Net: " + DoubleToString(netProfit, 2)
            }
         }
      }
      
      if(todayOrdersCount == 0)
      {
         logData += "No orders closed today\n";
      }
      else
      {
         logData += "\n";
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

void LogM1Candles()
{
   // Get the current M1 candle time
   datetime currentCandleTime = iTime(Symbol(), PERIOD_M1, 0);
   
   // Only log when a new candle has completed (when current candle time changes)
   if(lastM1CandleTime != 0 && currentCandleTime != lastM1CandleTime)
   {
      // Log the previous completed candle (index 1)
      datetime candleTime = iTime(Symbol(), PERIOD_M1, 1);
      double open = iOpen(Symbol(), PERIOD_M1, 1);
      double high = iHigh(Symbol(), PERIOD_M1, 1);
      double low = iLow(Symbol(), PERIOD_M1, 1);
      double close = iClose(Symbol(), PERIOD_M1, 1);
      
      // Create filename with date format: candles/YYYY-MM-DD-m1.csv
      string dateStr = TimeToString(candleTime, TIME_DATE);
      StringReplace(dateStr, ".", "-"); // Replace dots with dashes in date
      string fileName = "candles/" + dateStr + "-m1.csv";
      
      // Check if file exists to determine if we need to write header
      bool fileExists = false;
      int checkHandle = FileOpen(fileName, FILE_READ|FILE_TXT|FILE_CSV);
      if(checkHandle != INVALID_HANDLE)
      {
         fileExists = true;
         FileClose(checkHandle);
      }
      
      int fileHandle = FileOpen(fileName, FILE_READ|FILE_WRITE|FILE_TXT|FILE_CSV);
      
      if(fileHandle != INVALID_HANDLE)
      {
         // Move to end of file to append
         FileSeek(fileHandle, 0, SEEK_END);
         
         // Write header if this is a new file
         if(!fileExists)
         {
            string header = "Time;Open;High;Low;Close\n";
            FileWriteString(fileHandle, header);
         }
         
         // Format: Time;Open;High;Low;Close
         string candleData = TimeToString(candleTime, TIME_DATE|TIME_MINUTES) + ";" +
                           DoubleToString(open, 2) + ";" +
                           DoubleToString(high, 2) + ";" +
                           DoubleToString(low, 2) + ";" +
                           DoubleToString(close, 2) + "\n";
         
         FileWriteString(fileHandle, candleData);
         FileClose(fileHandle);
      }
      else
      {
         Print("Error opening M1 candle log file: ", GetLastError());
      }
   }
   
   // Update last candle time
   lastM1CandleTime = currentCandleTime;
}

void LogM15Candles()
{
   // Get the current M15 candle time
   datetime currentCandleTime = iTime(Symbol(), PERIOD_M15, 0);
   
   // Only log when a new candle has completed (when current candle time changes)
   if(lastM15CandleTime != 0 && currentCandleTime != lastM15CandleTime)
   {
      // Create filename with date and time format: candles/YYYY-MM-DD-HH-MM-m15.csv
      datetime candleTime = iTime(Symbol(), PERIOD_M15, 1);
      string dateStr = TimeToString(candleTime, TIME_DATE);
      StringReplace(dateStr, ".", "-"); // Replace dots with dashes in date
      string timeStr = TimeToString(candleTime, TIME_MINUTES);
      StringReplace(timeStr, ":", "-"); // Replace colons with dashes in time
      string fileName = "candles/" + dateStr + "-" + timeStr + "-m15.csv";
      
      int fileHandle = FileOpen(fileName, FILE_WRITE|FILE_TXT|FILE_CSV);
      
      if(fileHandle != INVALID_HANDLE)
      {
         // Write header
         string header = "Time;Open;High;Low;Close\n";
         FileWriteString(fileHandle, header);
         
         // Write 300 candles (previous 299 + current completed one at index 1)
         // Index 1 is the just-completed candle, indices 2-300 are the previous 299
         for(int i = 300; i >= 1; i--)
         {
            datetime candle_time = iTime(Symbol(), PERIOD_M15, i);
            double candle_open = iOpen(Symbol(), PERIOD_M15, i);
            double candle_high = iHigh(Symbol(), PERIOD_M15, i);
            double candle_low = iLow(Symbol(), PERIOD_M15, i);
            double candle_close = iClose(Symbol(), PERIOD_M15, i);
            
            // Format: Time;Open;High;Low;Close
            string candleData = TimeToString(candle_time, TIME_DATE|TIME_MINUTES) + ";" +
                              DoubleToString(candle_open, 2) + ";" +
                              DoubleToString(candle_high, 2) + ";" +
                              DoubleToString(candle_low, 2) + ";" +
                              DoubleToString(candle_close, 2) + "\n";
            
            FileWriteString(fileHandle, candleData);
         }
         
         FileClose(fileHandle);
      }
      else
      {
         Print("Error opening M15 candle log file: ", GetLastError());
      }
   }
   
   // Update last candle time
   lastM15CandleTime = currentCandleTime;
}

void CheckBreakEvenOrders()
{
   for(int i = 0; i < OrdersTotal(); i++)
   {
      if(OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
      {
         // Only process BUY and SELL orders
         if(OrderType() != OP_BUY && OrderType() != OP_SELL)
            continue;
            
         double currentPrice;
         double profitPoints;
         double newStopLoss;
	 bool modified;
         
         if(OrderType() == OP_BUY)
         {
            currentPrice = MarketInfo(OrderSymbol(), MODE_BID);
            profitPoints = currentPrice - OrderOpenPrice();
            newStopLoss = OrderOpenPrice() + bonus;
            
            // Check if profit has reached BE threshold and SL hasn't been moved to bonus yet
            if(profitPoints >= be && OrderStopLoss() < newStopLoss)
            {
               modified = OrderModify(OrderTicket(), OrderOpenPrice(), newStopLoss, OrderTakeProfit(), OrderExpiration(), clrBlue);
               if(modified)
               {
                  Print("BE triggered for BUY order ", OrderTicket(), 
                        " - SL moved to bonus: ", DoubleToString(newStopLoss, 5),
                        " (Profit: ", DoubleToString(profitPoints, 2), ")");
               }
               else
               {
                  Print("Failed to modify BUY order ", OrderTicket(), " Error: ", GetLastError());
               }
            }
         }
         else if(OrderType() == OP_SELL)
         {
            currentPrice = MarketInfo(OrderSymbol(), MODE_ASK);
            profitPoints = OrderOpenPrice() - currentPrice;
            newStopLoss = OrderOpenPrice() - bonus;
            
            // Check if profit has reached BE threshold and SL hasn't been moved to bonus yet
            if(profitPoints >= be && (OrderStopLoss() == 0 || OrderStopLoss() > newStopLoss))
            {
               modified = OrderModify(OrderTicket(), OrderOpenPrice(), newStopLoss, OrderTakeProfit(), OrderExpiration(), clrRed);
               if(modified)
               {
                  Print("BE triggered for SELL order ", OrderTicket(), 
                        " - SL moved to bonus: ", DoubleToString(newStopLoss, 5),
                        " (Profit: ", DoubleToString(profitPoints, 2), ")");
               }
               else
               {
                  Print("Failed to modify SELL order ", OrderTicket(), " Error: ", GetLastError());
               }
            }
         }
      }
   }
}

void Logs()
{
   // Log M1 candles (check on every tick for new candle)
   LogM1Candles();
   
   // Log M15 candles (check on every tick for new candle)
   LogM15Candles();
   
   datetime currentTime = TimeCurrent();
   
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
}

void OrderFiles()
{
   datetime currentTime = TimeCurrent();
   
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
   
   // Check for new orders
   if(currentTime - lastFileCheck >= 5)
   {
      ReadAndSendOrderFromFile();
      lastFileCheck = currentTime;
   }
}

void OnTick()
{
   // Load settings from file on first tick
   if(!settingsLoaded)
      ReadSettings();   
      
   Logs();
   OrderFiles();

// Main logic for every tick
//-----------------------------------------------------------------------

   // Check for BE
   CheckBreakEvenOrders();

//-----------------------------------------------------------------------

   hearbeat++;
   datetime currentTime = TimeCurrent();
   if(currentTime - lastFileCheck >= 30)
      Print("WD: " + version + " heartbeat: " + IntegerToString(hearbeat));
}
