// Order execution module for WD trading system
#property copyright "Copyright 2025"
#property link      ""
#property strict

input double lotSize = 0.01;
input int takeProfit = 200 * 100;
input int stopLoss = 50 * 100;

void ExecuteWdDecision(string decision, double lotSize, int takeProfit, int stopLoss, int slippage)
{
    if(decision == "BUY" || decision == "SELL")
    {        
        double tp = 0, sl = 0;
        int ticket = 0;

        int stopLevelPoints = (int)MarketInfo(Symbol(), MODE_STOPLEVEL);
        int freezeLevelPoints = (int)MarketInfo(Symbol(), MODE_FREEZELEVEL);
        double minStopDistance = MathMax(stopLevelPoints, freezeLevelPoints) * Point;
        double slDistance = MathMax(stopLoss * Point, minStopDistance);
        double tpDistance = MathMax(takeProfit * Point, minStopDistance);
        
        if(decision == "BUY")
        {
            tp = NormalizeDouble(Bid + tpDistance, Digits);
            sl = NormalizeDouble(Bid - slDistance, Digits);

            ResetLastError();
            ticket = OrderSend(Symbol(), OP_BUY, lotSize, NormalizeDouble(Ask, Digits), 
                slippage, sl, tp, "WD Tester Buy", 0, 0, clrGreen);
        }
        else if(decision == "SELL")
        {
            tp = NormalizeDouble(Ask - tpDistance, Digits);
            sl = NormalizeDouble(Ask + slDistance, Digits);

            ResetLastError();
            ticket = OrderSend(Symbol(), OP_SELL, lotSize, NormalizeDouble(Bid, Digits), 
                slippage, sl, tp, "WD Tester Sell", 0, 0, clrRed);
        }
        
        if(ticket > 0)
        {
            Print("Order opened successfully. Ticket: ", ticket);
        }
        else
        {
            int err = GetLastError();
            PrintFormat(
                "Order failed. Error: %d | side=%s Bid=%.*f Ask=%.*f SL=%.*f TP=%.*f stopLevelPoints=%d freezeLevelPoints=%d",
                err,
                decision,
                Digits, Bid,
                Digits, Ask,
                Digits, sl,
                Digits, tp,
                stopLevelPoints,
                freezeLevelPoints
            );
        }
    }
}
