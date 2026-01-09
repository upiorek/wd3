// Order execution module for WD trading system
#property copyright "Copyright 2025"
#property link      ""
#property strict

//--- OrderSend:
input double lotSize = 0.01;
input int takeProfit = 200 * 100;
input int stopLoss = 50 * 100;
input int slippage = 3 * 100;

//--- HasSimilarOpenOrder:
bool HasSimilarOpenOrder_enabled = true;
input int minDistance = 15;

//--- CheckBE:
bool CheckBE_enabled = true;
input int BEBonus = 25 * 100;

//-----------------------------------------------------------------------

string GetVersion()
{
    return "wd main version 1.2";
}

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

void CheckBE()
{
    if(CheckBE_enabled == false)
        return;

    double halfTP = takeProfit / 2.0;
    
    for(int i = OrdersTotal() - 1; i >= 0; i--)
    {
        if(!OrderSelect(i, SELECT_BY_POS, MODE_TRADES)) continue;
        if(OrderSymbol() != Symbol()) continue;
        if(OrderType() != OP_BUY && OrderType() != OP_SELL) continue;
        
        // Calculate current profit in points
        double currentPrice = OrderType() == OP_BUY ? Bid : Ask;
        double profitPoints = MathAbs(currentPrice - OrderOpenPrice()) / Point;
        
        // Check if profit is positive and > takeProfit/2
        bool isProfitable = (OrderType() == OP_BUY && currentPrice > OrderOpenPrice()) ||
                           (OrderType() == OP_SELL && currentPrice < OrderOpenPrice());
        
        if(isProfitable && profitPoints > halfTP)
        {
            // Calculate new SL at BE + bonus
            double newSL = NormalizeDouble(
                OrderType() == OP_BUY ? OrderOpenPrice() + BEBonus * Point : OrderOpenPrice() - BEBonus * Point,
                Digits
            );
            
            // Only modify if SL hasn't been moved to BE yet
            // For BUY: new SL should be higher than current SL
            // For SELL: new SL should be lower than current SL
            bool shouldModify = (OrderType() == OP_BUY && (OrderStopLoss() < OrderOpenPrice() || OrderStopLoss() == 0)) ||
                               (OrderType() == OP_SELL && (OrderStopLoss() > OrderOpenPrice() || OrderStopLoss() == 0));
            
            if(shouldModify)
            {
                ResetLastError();
                if(OrderModify(OrderTicket(), OrderOpenPrice(), newSL, OrderTakeProfit(), 0, clrBlue))
                {
                    Print("Break-even set: Ticket=", OrderTicket(), " Type=", OrderType() == OP_BUY ? "BUY" : "SELL",
                          " New SL=", newSL, " (BE+", BEBonus * Point, ")");
                }
                else
                {
                    Print("ERROR: Break-even failed: Ticket=", OrderTicket(), " Error=", GetLastError());
                }
            }
        }
    }
}

int ExecuteWdDecision(string decision)
{
    if(decision != "BUY" && decision != "SELL")
        return 0;
    
    bool isBuy = (decision == "BUY");
    int cmd = isBuy ? OP_BUY : OP_SELL;
    double price = NormalizeDouble(isBuy ? Ask : Bid, Digits);
    
    if(HasSimilarOpenOrder_enabled)
    {
        if(HasSimilarOpenOrder(cmd, price))
            return 0;
    }
    
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
        Print("ERROR: Order failed: ", decision, " Error=", GetLastError(), 
              " Price=", price, " SL=", sl, " TP=", tp);
    }
    return ticket;
}

