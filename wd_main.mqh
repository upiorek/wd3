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
input int minDistance = 10; // prices already * 100

//--- CheckBE:
bool CheckBE_enabled = true;
input int BEBonus = 25 * 100;

// weak closed on flip
input bool weak_closed_on_flip_enabled = false;

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
        if(!OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
            continue;
        if(OrderSymbol() != Symbol() || OrderType() != orderType)
            continue;
        
        int priceDiff = (int)MathAbs(OrderOpenPrice() - price);
        if(priceDiff <= minDistance)
        {
            HasSimilarOpenOrderDropped++;
            string order = OP_BUY ? "BUY" : "SELL";
            Print("Duplicate order skipped (", HasSimilarOpenOrderDropped, "): ",
            order, " at ", price, " diff ", priceDiff);
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

bool CheckWeakClosedOnFlip(string decision)
{
    // If we already have opposite WD trades open, do not open a new one.
    // Instead, close the worst-performing opposite order.
    // "Worst" = lowest (profit+swap+commission).
    int total = OrdersTotal();
    bool wantBuy = (decision == "BUY");
    int oppositeType = wantBuy ? OP_SELL : OP_BUY;

    int worstTicket = -1;
    double worstProfit = 0.0;
    bool haveWorst = false;

    for(int i = total - 1; i >= 0; i--)
    {
        if(!OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
            continue;
        if(OrderSymbol() != Symbol())
            continue;
        if(OrderType() != oppositeType)
            continue;

        string c = OrderComment();
        double p = (OrderProfit() + OrderSwap() + OrderCommission());
        if(!haveWorst || p < worstProfit)
        {
            worstProfit = p;
            worstTicket = OrderTicket();
            haveWorst = true;
        }
    }

    if(haveWorst && worstTicket > 0)
    {
        RefreshRates();
        if(OrderSelect(worstTicket, SELECT_BY_TICKET))
        {
            double closePrice = (OrderType() == OP_BUY) ? Bid : Ask;
            double lots = OrderLots();
            ResetLastError();
            if(OrderClose(worstTicket, lots, closePrice, slippage, clrNONE))
            {
                Print("Closed worst ", wantBuy ? "SELL" : "BUY", " instead of opening ", decision,
                      " Ticket=", worstTicket, " Profit=", DoubleToStr(worstProfit, 2));
                
                // closed worst
                return true;
            }
            else
            {
                Print("ERROR: Failed to close worst ", wantBuy ? "SELL" : "BUY", " Ticket=", worstTicket,
                      " Error=", GetLastError());
            }
        }
    }

    return false;
}

int ExecuteWdDecision(string decision)
{
    if(decision != "BUY" && decision != "SELL")
        return 0;
    
    bool isBuy = (decision == "BUY");
    int cmd = isBuy ? OP_BUY : OP_SELL;
    double price = NormalizeDouble(isBuy ? Ask : Bid, Digits);
    
    if(HasSimilarOpenOrder_enabled && HasSimilarOpenOrder(cmd, price))
        return 0;

    if (weak_closed_on_flip_enabled && CheckWeakClosedOnFlip(decision))
        return 0;
    
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

