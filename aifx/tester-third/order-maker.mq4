//+------------------------------------------------------------------+
//|                                              order-maker.mq4     |
//|                                                                  |
//|  Opens real orders based on odd/even logic and logs to CSV       |
//+------------------------------------------------------------------+
#property copyright "Copyright 2025"
#property link      ""
#property strict

// Specify subdirectory name (will be created in MT4 Files folder)
string FolderName = "m15_orders";
string version = "1.15";

datetime lastBarTime = 0;
int NumberOfCandles = 12;  // Initial log: 11 history + 1 entry (to match candle-maker starting at 20:45)

// Order management variables
int currentTicket = -1;
datetime entryTime = 0;
double entryPrice = 0.0;
string orderType = "";
int candleCount = 0;
bool slMovedToBE = false;
string currentFilename = "";
bool needToCreateLog = false;  // Flag to create log on next candle after entry

// Decision tracking
bool decisionMade = false;
string pendingOrderType = "";
datetime decisionTime = 0;
datetime decisionBarTime = 0;  // Track the bar time where decision was made

// Trading parameters
double TP_Points = 200.0;
double SL_Points = 50.0;
double BE_Trigger = 100.0;

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
   Print("order-maker EA initialized. Monitoring M15 candles...");
   Print("Files will be saved to: MT4\\MQL4\\Files\\", FolderName);
   Print("TP: +", TP_Points, " SL: -", SL_Points, " BE Trigger: +", BE_Trigger);
   
   // Don't make decision here - let first OnTick handle it so decision and trade happen together
   
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   // Close any open order on EA removal
   if(currentTicket >= 0)
   {
      CloseCurrentOrder("EA Stopped");
   }
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
      
      // If we have an active order, update the log
      if(currentTicket >= 0)
      {
         candleCount++;
         
         // If this is the first candle after opening and we need to create log
         if(needToCreateLog)
         {
            CreateInitialLog();
            needToCreateLog = false;
         }
         else
         {
            UpdateOrderLog();
            
            // Close order after 10 candles (to match _mod file structure)
            // Close at the START of 11th candle (after 10 complete candles logged)
            if(candleCount >= 10)
            {
               CloseOrderManually();
            }
         }
      }
      else if(decisionMade)
      {
         // Decision was made on previous candle, now open the order
         OpenNewOrder();
         decisionMade = false;
         pendingOrderType = "";
      }
      else
      {
         // No active order and no pending decision - make a decision for next candle
         // Analyze bar[0] (current candle) and will trade on next candle
         MakeDecisionOnBar(0);
         // Don't open immediately - wait for next candle
      }
      
      lastBarTime = currentBarTime;
   }
   else
   {
      // Within the same candle - check for BE trigger and TP/SL hits
      if(currentTicket >= 0)
      {
         CheckOrderStatus();
      }
   }
}

//+------------------------------------------------------------------+
//| Make decision based on current candle                            |
//+------------------------------------------------------------------+
void MakeDecision()
{
   MakeDecisionOnBar(0);
}

//+------------------------------------------------------------------+
//| Make decision based on specific bar                              |
//+------------------------------------------------------------------+
void MakeDecisionOnBar(int barIndex)
{
   // Get candle open price at specified bar
   double openPrice = iOpen(Symbol(), PERIOD_M15, barIndex);
   datetime barTime = iTime(Symbol(), PERIOD_M15, barIndex);
   
   // Determine BUY or SELL based on odd/even
   // Convert price to integer (remove decimal point)
   int priceInt = (int)(openPrice * 100); // Use 2 decimal precision
   bool isOdd = (priceInt % 2 == 1);
   
   pendingOrderType = isOdd ? "BUY" : "SELL";
   decisionMade = true;
   decisionTime = TimeCurrent();
   decisionBarTime = barTime;  // Store the bar time where decision was made
   
   Print("Decision made on bar[", barIndex, "] at ", TimeToString(barTime), 
         ": Open price ", openPrice, " is ", isOdd ? "ODD" : "EVEN", 
         " -> Will ", pendingOrderType, " on next candle");
}

//+------------------------------------------------------------------+
//| Open a new order based on odd/even logic                         |
//+------------------------------------------------------------------+
void OpenNewOrder()
{
   // Use the pending decision made on the previous candle
   if(pendingOrderType == "")
   {
      Print("Error: OpenNewOrder called but no pending decision!");
      return;
   }
   
   // Check if file for this time already exists
   datetime now = TimeCurrent();
   string filename = StringFormat("%s\\%02d-%02d-%02d-%02d-%02d.csv",
                                   FolderName,
                                   TimeYear(now) % 100,
                                   TimeMonth(now),
                                   TimeDay(now),
                                   TimeHour(now),
                                   TimeMinute(now));
   
   // If file exists, skip this run
   if(FileIsExist(filename, 0))
   {
      Print("File already exists: ", filename, " - skipping this trade");
      return;
   }
   
   // Set order type from pending decision
   orderType = pendingOrderType;
   int orderCmd = (orderType == "BUY") ? OP_BUY : OP_SELL;
   
   // Get current price
   double price = (orderCmd == OP_BUY) ? Ask : Bid;
   
   // Calculate TP and SL
   // For indices, points are actual price units, not pips
   double tp = 0, sl = 0;
   if(orderCmd == OP_BUY)
   {
      tp = price + TP_Points;
      sl = price - SL_Points;
   }
   else
   {
      tp = price - TP_Points;
      sl = price + SL_Points;
   }
   
   // Open the order
   int ticket = OrderSend(Symbol(), orderCmd, 0.01, price, 3, sl, tp, 
                          "OrderMaker-" + orderType, 12345, 0, 
                          orderCmd == OP_BUY ? clrBlue : clrRed);
   
   if(ticket < 0)
   {
      Print("Error opening order: ", GetLastError());
      return;
   }
   
   // Store order details
   currentTicket = ticket;
   entryTime = TimeCurrent();
   entryPrice = price;
   candleCount = 0;
   slMovedToBE = false;
   currentFilename = filename;
   needToCreateLog = true;  // Set flag to create log on next candle
   
   Print("Opened ", orderType, " order #", ticket, " at ", entryPrice);
   Print("Will create log file on next candle after entry candle completes");
   
   // Don't create log yet - wait for next candle
}

//+------------------------------------------------------------------+
//| Create initial log file with past candles                        |
//+------------------------------------------------------------------+
void CreateInitialLog()
{
   int fileHandle = FileOpen(currentFilename, FILE_WRITE|FILE_TXT);
   
   if(fileHandle == INVALID_HANDLE)
   {
      Print("Error opening file: ", currentFilename, " Error code: ", GetLastError());
      return;
   }
   
   // Write header
   FileWriteString(fileHandle, "Time;Open;High;Low;Close\n");
   
   // Write last N candles (from oldest to newest), skip bar[0] (current incomplete candle)
   int period = PERIOD_M15;
   string symbol = Symbol();
   
   for(int i = NumberOfCandles - 1; i >= 1; i--)
   {
      datetime time = iTime(symbol, period, i);
      double open = iOpen(symbol, period, i);
      double high = iHigh(symbol, period, i);
      double low = iLow(symbol, period, i);
      double close = iClose(symbol, period, i);
      
      string line = TimeToString(time, TIME_DATE|TIME_MINUTES) + ";" +
                    DoubleToString(open, Digits) + ";" +
                    DoubleToString(high, Digits) + ";" +
                    DoubleToString(low, Digits) + ";" +
                    DoubleToString(close, Digits);
      
      // Add signal marker on the decision candle (match by bar time)
      if(time == decisionBarTime)
      {
         line += " " + orderType;
      }
      
      // Add initial distances on the entry candle (bar[1] when log is created)
      if(i == 1)
      {
         // Calculate initial distances based on completed entry candle
         double distSL = 0, distTP = 0;
         if(orderType == "BUY")
         {
            distSL = low - entryPrice;
            distTP = high - entryPrice;
         }
         else
         {
            distSL = entryPrice - high;
            distTP = entryPrice - low;
         }
         
         line += " distSL=" + DoubleToString(distSL, 2) + 
                 " distTP=" + DoubleToString(distTP, 2);
      }
      
      FileWriteString(fileHandle, line + "\n");
   }
   
   FileClose(fileHandle);
   Print("Created initial log: ", currentFilename);
}

//+------------------------------------------------------------------+
//| Update order log with new candle data                            |
//+------------------------------------------------------------------+
void UpdateOrderLog()
{
   if(currentFilename == "" || currentTicket < 0)
      return;
   
   // Read existing file
   int readHandle = FileOpen(currentFilename, FILE_READ|FILE_TXT);
   if(readHandle == INVALID_HANDLE)
   {
      Print("Error reading file: ", currentFilename);
      return;
   }
   
   string fileContent = "";
   while(!FileIsEnding(readHandle))
   {
      fileContent += FileReadString(readHandle);
      if(!FileIsEnding(readHandle))
         fileContent += "\n";
   }
   FileClose(readHandle);
   
   // Get current candle data - use bar[1] (completed previous candle)
   int period = PERIOD_M15;
   string symbol = Symbol();
   datetime time = iTime(symbol, period, 1);
   double open = iOpen(symbol, period, 1);
   double high = iHigh(symbol, period, 1);
   double low = iLow(symbol, period, 1);
   double close = iClose(symbol, period, 1);
   
   // Calculate distances
   double distSL = 0, distTP = 0;
   if(orderType == "BUY")
   {
      distSL = low - entryPrice;
      distTP = high - entryPrice;
   }
   else
   {
      distSL = entryPrice - high;
      distTP = entryPrice - low;
   }
   
   // Build new line
   string newLine = TimeToString(time, TIME_DATE|TIME_MINUTES) + ";" +
                    DoubleToString(open, Digits) + ";" +
                    DoubleToString(high, Digits) + ";" +
                    DoubleToString(low, Digits) + ";" +
                    DoubleToString(close, Digits) + 
                    " distSL=" + DoubleToString(distSL, 2) + 
                    " distTP=" + DoubleToString(distTP, 2);
   
   // Add BE marker if SL moved to BE
   if(slMovedToBE)
   {
      newLine += " BE";
   }
   
   // Rewrite file with new line
   int writeHandle = FileOpen(currentFilename, FILE_WRITE|FILE_TXT);
   if(writeHandle == INVALID_HANDLE)
   {
      Print("Error writing file: ", currentFilename);
      return;
   }
   
   FileWriteString(writeHandle, fileContent);
   if(StringLen(fileContent) > 0 && StringGetChar(fileContent, StringLen(fileContent) - 1) != '\n')
      FileWriteString(writeHandle, "\n");
   FileWriteString(writeHandle, newLine + "\n");
   FileClose(writeHandle);
}

//+------------------------------------------------------------------+
//| Check order status for BE trigger and TP/SL hits                 |
//+------------------------------------------------------------------+
void CheckOrderStatus()
{
   if(currentTicket < 0)
      return;
   
   // Select the order
   if(!OrderSelect(currentTicket, SELECT_BY_TICKET))
   {
      Print("Error selecting order #", currentTicket);
      return;
   }
   
   // Check if order is still open
   if(OrderCloseTime() > 0)
   {
      // Order was closed (TP or SL hit)
      double closePrice = OrderClosePrice();
      double profit = OrderProfit();
      
      string result = "";
      if(profit > 0)
         result = (profit >= TP_Points * OrderLots() * 100) ? "TP" : "Partial Profit";
      else if(profit < 0)
         result = slMovedToBE ? "BE" : "SL";
      else
         result = "BE";
      
      Print("Order #", currentTicket, " closed: ", result, " Profit: ", profit);
      
      // Update log with final result
      AppendFinalResult(result);
      
      // Reset order tracking
      currentTicket = -1;
      entryTime = 0;
      entryPrice = 0;
      orderType = "";
      candleCount = 0;
      slMovedToBE = false;
      currentFilename = "";
      return;
   }
   
   // Check if we should move SL to BE
   if(!slMovedToBE)
   {
      double currentPrice = (orderType == "BUY") ? Bid : Ask;
      double distanceToEntry = 0;
      
      if(orderType == "BUY")
         distanceToEntry = currentPrice - entryPrice;
      else
         distanceToEntry = entryPrice - currentPrice;
      
      // If profit reached BE trigger, move SL to entry
      if(distanceToEntry >= BE_Trigger)
      {
         double newSL = entryPrice;
         
         if(OrderModify(currentTicket, entryPrice, newSL, OrderTakeProfit(), 0, clrYellow))
         {
            Print("Moved SL to Break Even for order #", currentTicket);
            slMovedToBE = true;
         }
         else
         {
            Print("Error moving SL to BE: ", GetLastError());
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Close current order manually                                     |
//+------------------------------------------------------------------+
void CloseCurrentOrder(string reason)
{
   if(currentTicket < 0)
      return;
   
   if(!OrderSelect(currentTicket, SELECT_BY_TICKET))
   {
      Print("Error selecting order for closure #", currentTicket);
      return;
   }
   
   if(OrderCloseTime() > 0)
   {
      Print("Order #", currentTicket, " already closed");
      currentTicket = -1;
      return;
   }
   
   double closePrice = (orderType == "BUY") ? Bid : Ask;
   
   if(OrderClose(currentTicket, OrderLots(), closePrice, 3, clrGray))
   {
      Print("Closed order #", currentTicket, " - Reason: ", reason);
      
      // Calculate result
      double profit = (orderType == "BUY") ? (closePrice - entryPrice) : (entryPrice - closePrice);
      string result = "CLOSED_" + IntegerToString(candleCount) + "C";
      
      // Update log with final result
      AppendFinalResult(result);
   }
   else
   {
      Print("Error closing order #", currentTicket, ": ", GetLastError());
   }
   
   // Reset order tracking
   currentTicket = -1;
   entryTime = 0;
   entryPrice = 0;
   orderType = "";
   candleCount = 0;
   slMovedToBE = false;
   currentFilename = "";
}

//+------------------------------------------------------------------+
//| Close order manually after N candles                             |
//+------------------------------------------------------------------+
void CloseOrderManually()
{
   CloseCurrentOrder("10 candles reached");
}

//+------------------------------------------------------------------+
//| Append final result to log file                                  |
//+------------------------------------------------------------------+
void AppendFinalResult(string result)
{
   if(currentFilename == "")
      return;
   
   // Read existing file
   int readHandle = FileOpen(currentFilename, FILE_READ|FILE_TXT);
   if(readHandle == INVALID_HANDLE)
   {
      Print("Error reading file for final result: ", currentFilename);
      return;
   }
   
   string fileContent = "";
   while(!FileIsEnding(readHandle))
   {
      string line = FileReadString(readHandle);
      fileContent += line;
      if(!FileIsEnding(readHandle))
         fileContent += "\n";
   }
   FileClose(readHandle);
   
   // Find last line and append result
   int lastNewline = -1;
   for(int i = StringLen(fileContent) - 2; i >= 0; i--)
   {
      if(StringGetChar(fileContent, i) == '\n')
      {
         lastNewline = i;
         break;
      }
   }
   
   if(lastNewline >= 0)
   {
      string beforeLast = StringSubstr(fileContent, 0, lastNewline + 1);
      string lastLine = StringSubstr(fileContent, lastNewline + 1);
      
      // Remove trailing newline/spaces
      while(StringLen(lastLine) > 0)
      {
         int lastChar = StringGetChar(lastLine, StringLen(lastLine) - 1);
         if(lastChar == '\n' || lastChar == '\r' || lastChar == ' ')
            lastLine = StringSubstr(lastLine, 0, StringLen(lastLine) - 1);
         else
            break;
      }
      
      // Append result marker
      string newLastLine = lastLine + " " + result;
      
      // Rebuild file content
      fileContent = beforeLast + newLastLine + "\n";
   }
   else
   {
      // Only one line or empty file - just append to it
      while(StringLen(fileContent) > 0)
      {
         int lastChar = StringGetChar(fileContent, StringLen(fileContent) - 1);
         if(lastChar == '\n' || lastChar == '\r' || lastChar == ' ')
            fileContent = StringSubstr(fileContent, 0, StringLen(fileContent) - 1);
         else
            break;
      }
      fileContent += " " + result + "\n";
   }
   
   // Write back to file
   int writeHandle = FileOpen(currentFilename, FILE_WRITE|FILE_TXT);
   if(writeHandle == INVALID_HANDLE)
   {
      Print("Error writing final result: ", currentFilename);
      return;
   }
   
   FileWriteString(writeHandle, fileContent);
   FileClose(writeHandle);
   
   Print("Added final result to log: ", result);
}
