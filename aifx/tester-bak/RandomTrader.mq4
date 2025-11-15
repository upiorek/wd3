//+------------------------------------------------------------------+
//|                                                 RandomTrader.mq4 |
//|                        Simple Random Trading EA for US100.f      |
//+------------------------------------------------------------------+
#property copyright "Trading System"
#property link      ""
#property version   "1.00"
#property strict

// Input parameters
input string TestDate = "2025-11-09";  // Test Date (YYYY-MM-DD)
input int CandleInterval = 5;          // Number of M15 candles between trades
input double LotSize = 0.01;           // Lot size for trades
input int StopLossPips = 50;           // Stop loss in pips
input int MagicNumber = 123456;        // Magic number for this EA

// Global variables
datetime lastTradeBar = 0;
int barCounter = 0;
int tradesCount = 0;

//+------------------------------------------------------------------+
//| Expert initialization function                                     |
//+------------------------------------------------------------------+
int OnInit()
{
   Print("RandomTrader EA initialized");
   Print("Test Date: ", TestDate);
   Print("Trading on: ", Symbol());
   Print("Timeframe: M15");
   Print("Candle Interval: ", CandleInterval);
   Print("Lot Size: ", LotSize);
   Print("Stop Loss: ", StopLossPips, " pips");
   Print("Take Profit: ", (StopLossPips * 3), " pips (1:3 ratio)");
   
   // Seed random number generator
   MathSrand((int)TimeLocal());
   
   lastTradeBar = 0;
   barCounter = 0;
   tradesCount = 0;
   
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   Print("RandomTrader EA stopped. Total trades executed: ", tradesCount);
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   // Check if we have a new bar
   datetime currentBar = iTime(Symbol(), PERIOD_M15, 0);
   
   if(currentBar != lastTradeBar)
   {
      lastTradeBar = currentBar;
      barCounter++;
      
      // Execute trade every CandleInterval candles
      if(barCounter >= CandleInterval)
      {
         ExecuteRandomTrade();
         barCounter = 0;
      }
   }
}

//+------------------------------------------------------------------+
//| Execute a random buy or sell trade                               |
//+------------------------------------------------------------------+
void ExecuteRandomTrade()
{
   // Randomly decide buy (0) or sell (1)
   int tradeType = MathRand() % 2;
   
   double price;
   int cmd;
   color arrowColor;
   string tradeTypeStr;
   
   // Get point value and adjust for 5-digit brokers
   double point = Point;
   if(Digits == 5 || Digits == 3)
      point *= 10;
   
   // Calculate SL and TP distances
   double slDistance = StopLossPips * point;
   double tpDistance = StopLossPips * 3 * point; // 1:3 risk-reward ratio
   
   double sl, tp;
   
   if(tradeType == 0)
   {
      // Buy
      cmd = OP_BUY;
      price = Ask;
      sl = price - slDistance;  // SL below entry
      tp = price + tpDistance;  // TP above entry (3x SL distance)
      arrowColor = clrBlue;
      tradeTypeStr = "BUY";
   }
   else
   {
      // Sell
      cmd = OP_SELL;
      price = Bid;
      sl = price + slDistance;  // SL above entry
      tp = price - tpDistance;  // TP below entry (3x SL distance)
      arrowColor = clrRed;
      tradeTypeStr = "SELL";
   }
   
   // Normalize SL and TP prices
   sl = NormalizeDouble(sl, Digits);
   tp = NormalizeDouble(tp, Digits);
   
   // Execute the trade
   int ticket = OrderSend(Symbol(), cmd, LotSize, price, 3, sl, tp, 
                         "Random Trade", MagicNumber, 0, arrowColor);
   
   if(ticket > 0)
   {
      tradesCount++;
      Print("Trade #", tradesCount, " executed: ", tradeTypeStr, 
            " | Ticket: ", ticket, 
            " | Price: ", DoubleToStr(price, Digits),
            " | SL: ", DoubleToStr(sl, Digits),
            " | TP: ", DoubleToStr(tp, Digits),
            " | Lot: ", DoubleToStr(LotSize, 2),
            " | Time: ", TimeToStr(TimeCurrent(), TIME_DATE|TIME_MINUTES));
   }
   else
   {
      int error = GetLastError();
      Print("Order failed! Error: ", error, " - ", ErrorDescription(error));
   }
}

//+------------------------------------------------------------------+
//| Error description function                                        |
//+------------------------------------------------------------------+
string ErrorDescription(int error)
{
   string errorString;
   
   switch(error)
   {
      case 0:    errorString="No error"; break;
      case 1:    errorString="No error, trade conditions not changed"; break;
      case 2:    errorString="Common error"; break;
      case 3:    errorString="Invalid trade parameters"; break;
      case 4:    errorString="Trade server is busy"; break;
      case 5:    errorString="Old version of the client terminal"; break;
      case 6:    errorString="No connection with trade server"; break;
      case 7:    errorString="Not enough rights"; break;
      case 8:    errorString="Too frequent requests"; break;
      case 9:    errorString="Malfunctional trade operation"; break;
      case 64:   errorString="Account disabled"; break;
      case 65:   errorString="Invalid account"; break;
      case 128:  errorString="Trade timeout"; break;
      case 129:  errorString="Invalid price"; break;
      case 130:  errorString="Invalid stops"; break;
      case 131:  errorString="Invalid trade volume"; break;
      case 132:  errorString="Market is closed"; break;
      case 133:  errorString="Trade is disabled"; break;
      case 134:  errorString="Not enough money"; break;
      case 135:  errorString="Price changed"; break;
      case 136:  errorString="Off quotes"; break;
      case 137:  errorString="Broker is busy"; break;
      case 138:  errorString="Requote"; break;
      case 139:  errorString="Order is locked"; break;
      case 140:  errorString="Long positions only allowed"; break;
      case 141:  errorString="Too many requests"; break;
      case 145:  errorString="Modification denied because order too close to market"; break;
      case 146:  errorString="Trade context is busy"; break;
      case 147:  errorString="Expirations are denied by broker"; break;
      case 148:  errorString="Amount of open and pending orders has reached the limit"; break;
      default:   errorString="Unknown error: "+IntegerToString(error); break;
   }
   
   return(errorString);
}
