// Order execution module for WD trading system
#property copyright "Copyright 2025"
#property link      ""
#property strict

//--- OrderSend:
input double lotSize = 0.01;
input int takeProfit = 200 * 100;
input int stopLoss = 50 * 100;
input int slippage = 300;

//--- HasSimilarOpenOrder:
bool HasSimilarOpenOrder_enabled = true;
input int minDistance = 15;

//-----------------------------------------------------------------------

int HasSimilarOpenOrderDropped = 0 ;
bool HasSimilarOpenOrder(int orderType, double price)
{
    for(int i = OrdersTotal() - 1; i >= 0; i--)
    {
        if(!OrderSelect(i, SELECT_BY_POS, MODE_TRADES)) continue;
        if(OrderSymbol() != Symbol() || OrderType() != orderType) continue;
        
        double priceDiff = MathAbs(OrderOpenPrice() - price) / Point;
        if(priceDiff <= minDistance)
        {
            HasSimilarOpenOrderDropped++;
            Print("Duplicate order skipped (", HasSimilarOpenOrderDropped, "): ", orderType == OP_BUY ? "BUY" : "SELL", 
                  " at ", price, " (diff=", priceDiff, " points)");
            return true;
        }
    }
    return false;
}

void ExecuteWdDecision(string decision)
{
    if(decision != "BUY" && decision != "SELL") return;
    
    bool isBuy = (decision == "BUY");
    int cmd = isBuy ? OP_BUY : OP_SELL;
    double price = NormalizeDouble(isBuy ? Ask : Bid, Digits);
    
    if(HasSimilarOpenOrder_enabled)
        if(HasSimilarOpenOrder(cmd, price)) return;
    
    int stopLevelPoints = (int)MarketInfo(Symbol(), MODE_STOPLEVEL);
    int freezeLevelPoints = (int)MarketInfo(Symbol(), MODE_FREEZELEVEL);
    double minStopDistance = MathMax(stopLevelPoints, freezeLevelPoints) * Point;
    double slDist = MathMax(stopLoss * Point, minStopDistance);
    double tpDist = MathMax(takeProfit * Point, minStopDistance);
    
    double tp = NormalizeDouble(isBuy ? Bid + tpDist : Ask - tpDist, Digits);
    double sl = NormalizeDouble(isBuy ? Bid - slDist : Ask + slDist, Digits);
    
    ResetLastError();
    int ticket = OrderSend(Symbol(), cmd, lotSize, price, slippage, sl, tp, 
                           "WD " + decision, 0, 0, isBuy ? clrGreen : clrRed);
    
    if(ticket > 0)
    {
        Print("Order opened: ", decision, " Ticket=", ticket);
    }
    else
    {
        Print("Order failed: ", decision, " Error=", GetLastError(), 
              " Price=", price, " SL=", sl, " TP=", tp);
    }
}

