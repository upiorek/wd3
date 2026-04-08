// Order execution module for WD trading system
#property copyright "Copyright 2025-2026"
#property link      ""
#property strict

//--- OrderSend:
input double lotSize = 0.01;
input int takeProfit = 200 * 100;
input int stopLoss = 50 * 100;
input int slippage = 3 * 100;

//--- HasSimilarOpenOrder:
bool HasSimilarOpenOrder_enabled = true;
input int minDistance = 25;

//--- CheckBE:
bool CheckBE_enabled = true;
input int BEBonus = 25 * 100;

// weak closed on flip
input bool weak_closed_on_flip_enabled = true;
bool weak_closed_on_flip_min_opp_enabled = true;
int weak_closed_on_flip_min_opp = 4;

//--- CheckSetupTP:
input bool CheckSetupTP_enabled = true;
input int setupTP = 500 * 100;

//--- OrderAboveOrBelow:
input bool OrderAboveOrBelow_enabled = true;
input int OrderAboveOrBelowTolerance = 3;
input int OrderAboveOrBelowGap = 50;

//--- ThirdOrderGap
input bool ThirdOrderGap_enabled = true;
input int thirdOrderGap = 100;

//--- SetAllOrdersSlToMaxSl
input bool SetAllOrdersSlToMaxSl_enabled = true;
input int howManyOrdersSlToMaxSl = 3;

//--- CloseIfNoProfitAfterNCandles
input bool CloseIfNoProfitAfterNCandles_enabled = false;
input int CloseIfNoProfitAfterNCandles = 10;

//--- MinLineAge
// lines with age < MinLineAge will have grey color 
input bool MinLineAge_enabled = false;
input int MinLineAge = 1;

//--- TrailingTP
// jeżeli protif dotrze do TP dajemy trailing stop na pioziomie BEBonus
input bool TrailingTP_enabled = true;

//-----------------------------------------------------------------------

string GetVersion()
{
    return "wd main version 1.45";
}

void Log(string message)
{
   Print("Logged: " + message);

   // Get current date for filename
   string today = TimeToString(TimeCurrent(), TIME_DATE);
   StringReplace(today, ".", "-");
   string filename = "wd-" + today + ".log";
   
   int fileHandle = FileOpen(filename, FILE_READ|FILE_WRITE|FILE_TXT);
   
   if(fileHandle != INVALID_HANDLE)
   {
      // Seek to end to append
      FileSeek(fileHandle, 0, SEEK_END);
      
      string logEntry = TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS) + " | ";
      logEntry += message + "\n";
      
      FileWriteString(fileHandle, logEntry);
      FileClose(fileHandle);
   }
   else
   {
      Print("Failed to open log file: ", GetLastError());
   }
}

int HasSimilarOpenOrderDropped = 0;
bool HasSimilarOpenOrder(int orderType, double price)
{
    for(int i = OrdersTotal() - 1; i >= 0; i--)
    {
        if(!OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
            continue;
        
        // NOTE: do not check orderType
        if(OrderSymbol() != Symbol())
            continue;
        
        int priceDiff = (int)MathAbs(OrderOpenPrice() - price);
        if(priceDiff <= minDistance)
        {
            HasSimilarOpenOrderDropped++;
            string order = orderType == OP_BUY ? "BUY" : "SELL";
            string str = "Duplicate order skipped (" + IntegerToString(HasSimilarOpenOrderDropped) + "): " +
                order + " at " + DoubleToStr(price, 2) + " diff " + DoubleToStr(priceDiff, 2) +
                " minDistance: " + IntegerToString(minDistance);
            // Print(str);
            Log(str);
            return true;
        }
    }
    return false;
}

void SetAllOrdersSlToMaxSl(int orderType)
{
    if(orderType != OP_SELL && orderType != OP_BUY)
        return;

    double targetSL = 0;
    int sourceSLTicket = -1;
    int sells = 0;
    int buys = 0;

    for(int j = OrdersTotal() - 1; j >= 0; j--)
    {
        if(!OrderSelect(j, SELECT_BY_POS, MODE_TRADES))
            continue;
        if(OrderSymbol() != Symbol() || OrderType() != orderType)
            continue;

        double sl = OrderStopLoss();
        if(sl <= 0)
            continue;

        if(orderType == OP_SELL)
            sells++;
        if(orderType == OP_BUY)
            buys++;

        if(orderType == OP_SELL && (targetSL == 0 || sl > targetSL))
        {
            targetSL = sl;
            sourceSLTicket = OrderTicket();
        }

        if(orderType == OP_BUY && (targetSL == 0 || sl < targetSL))
        {
            targetSL = sl;
            sourceSLTicket = OrderTicket();
        }
    }

    Log("Currently open sells: " + IntegerToString(sells) + " buys: " + IntegerToString(buys));
    int activeOrders = (orderType == OP_SELL) ? sells : buys;
    if(activeOrders < howManyOrdersSlToMaxSl)
    {
    	//Log("Not enough!, min is: " + IntegerToString(howManyOrdersSlToMaxSl));
        return;
    }

    if(targetSL > 0)
    {
        int syncedCount = 0;
        for(int k = OrdersTotal() - 1; k >= 0; k--)
        {
            if(!OrderSelect(k, SELECT_BY_POS, MODE_TRADES))
                continue;
            if(OrderSymbol() != Symbol() || OrderType() != orderType)
                continue;

            double currentSL = OrderStopLoss();
            if(MathAbs(currentSL - targetSL) <= (Point / 2.0))
                continue;

            int ticketToModify = OrderTicket();
            double openPriceToKeep = OrderOpenPrice();
            double tpToKeep = OrderTakeProfit();

            ResetLastError();
            if(OrderModify(ticketToModify, openPriceToKeep, targetSL, tpToKeep, 0, clrRed))
            {
                syncedCount++;
            }
            else
            {
                string orderName = orderType == OP_BUY ? "BUY" : "SELL";
                Log("ERROR: " + orderName + " SL sync failed Ticket=" + IntegerToString(ticketToModify) +
                    " Error=" + IntegerToString(GetLastError()));
            }
        }

        if(syncedCount > 0)
        {
            string orderName = orderType == OP_BUY ? "BUY" : "SELL";
            string targetName = orderType == OP_BUY ? "lowest" : "highest";
            Log(orderName + " SL synced to " + targetName + " SL=" + DoubleToStr(targetSL, 2) +
                " sourceTicket=" + IntegerToString(sourceSLTicket) +
                " modified=" + IntegerToString(syncedCount));
        }
    }
}

int HasSimilarOpenOrderThirdDropped = 0;
bool HasSimilarOpenOrderThird(int orderType, double price)
{
    int orderTypesFound = 1;
    double priceForSell = 0;
    double priceForBuy = 0;

    for(int i = OrdersTotal() - 1; i >= 0; i--)
    {
        if(!OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
            continue;
        if(OrderSymbol() != Symbol() || OrderType() != orderType)
            continue;
            
            if(orderType == OP_SELL &&
	     (priceForSell == 0 || priceForSell > OrderOpenPrice()))
	      priceForSell = OrderOpenPrice();
            if(orderType == OP_BUY && 
	    (priceForBuy == 0 || priceForBuy < OrderOpenPrice()))
	      priceForBuy = OrderOpenPrice();
	      
       orderTypesFound++;
       //Log("orderTypesFound: " + IntegerToString(orderTypesFound));
	if (orderTypesFound <= 2)
	    continue;

	int priceDiff = 0;
	if(priceForBuy != 0)
	{
	    Log("priceForBuy: " + DoubleToStr(priceForBuy, 2));
	    priceDiff = (int)MathAbs(priceForBuy - price);
	}
	if(priceForSell != 0)
	{
	    Log("priceForSell: " + DoubleToStr(priceForSell, 2));
	    priceDiff = (int)MathAbs(priceForSell - price);
	}
        
        //Log("priceDiff: " + IntegerToString(priceDiff));
        if(priceDiff <= thirdOrderGap)
        {
            HasSimilarOpenOrderThirdDropped++;
            string order = orderType == OP_BUY ? "BUY" : "SELL";
            Log("Third+ order skipped (" + IntegerToString(HasSimilarOpenOrderThirdDropped) + "): " +
                order + " at " + DoubleToString(price) + " diff " + DoubleToString(priceDiff) +
                " thirdOrderGap: " + IntegerToString(thirdOrderGap));
            return true;
        }
    }
    return false;
}

void CheckSetupTP()
{
    if (CheckSetupTP_enabled == false)
        return;
    
    int profitPoints = 0;
    int orderCount = 0;
    
    for(int i = OrdersTotal() - 1; i >= 0; i--)
    {
        if(!OrderSelect(i, SELECT_BY_POS, MODE_TRADES)) continue;
        if(OrderSymbol() != Symbol()) continue;
        if(OrderType() != OP_BUY && OrderType() != OP_SELL) continue;

        double currentPrice = OrderType() == OP_BUY ? Bid : Ask;
        profitPoints += (int)(MathAbs(currentPrice - OrderOpenPrice()) / Point);
        orderCount++;
    }
   
    if(profitPoints > setupTP)
    {
        Log("Setup TP reached! Total profit: " + IntegerToString(profitPoints) + 
            " > " + IntegerToString(setupTP) + " - Closing all " + IntegerToString(orderCount) + " orders");
        
        int closedCount = 0;
        int failedCount = 0;
        
        for(int i = OrdersTotal() - 1; i >= 0; i--)
        {
            if(!OrderSelect(i, SELECT_BY_POS, MODE_TRADES)) continue;
            if(OrderSymbol() != Symbol()) continue;
            if(OrderType() != OP_BUY && OrderType() != OP_SELL) continue;
            
            RefreshRates();
            double closePrice = (OrderType() == OP_BUY) ? Bid : Ask;
            double lots = OrderLots();
            int ticket = OrderTicket();
            
            ResetLastError();
            if(OrderClose(ticket, lots, closePrice, slippage, clrYellow))
            {
                closedCount++;
		string type = OrderType() == OP_BUY ? "BUY" : "SELL";
                Log("Closed order #" + IntegerToString(ticket) + " | Type: " + type);
            }
            else
            {
                failedCount++;
                Log("ERROR: Failed to close order #" + IntegerToString(ticket) +
		    " | Error: " + IntegerToString(GetLastError()));
            }
        }
        
        Log("Setup TP complete: Closed " + IntegerToString(closedCount) +
	    " orders | Failed: " + IntegerToString(failedCount));
    }
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
		            string type = OrderType() == OP_BUY ? "BUY" : "SELL";
                    Log("Break-even set: Ticket=" + IntegerToString(OrderTicket()) + " Type=" + type +
                          " New SL=" + DoubleToString(newSL) + " (BE+" + DoubleToString(BEBonus * Point) + ")");
                }
                else
                {
                    Log("ERROR: Break-even failed: Ticket=" + IntegerToString(OrderTicket()) +
		                " Error=" + IntegerToString(GetLastError()));
                }
            }
        }
    }
}

void CheckTrailingTP()
{
    if(!TrailingTP_enabled)
        return;
    if(takeProfit <= 0)
        return;
    if(BEBonus < 0)
        return;

    for(int i = OrdersTotal() - 1; i >= 0; i--)
    {
        if(!OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
            continue;
        if(OrderSymbol() != Symbol())
            continue;
        if(OrderType() != OP_BUY && OrderType() != OP_SELL)
            continue;

        int type = OrderType();
        double currentPrice = type == OP_BUY ? Bid : Ask;
        bool isProfitable = (type == OP_BUY && currentPrice > OrderOpenPrice()) ||
                           (type == OP_SELL && currentPrice < OrderOpenPrice());
        if(!isProfitable)
            continue;

        double profitPoints = MathAbs(currentPrice - OrderOpenPrice()) / Point;
        if(profitPoints < takeProfit)
            continue;

        double newSL = NormalizeDouble(
            type == OP_BUY ? currentPrice - BEBonus * Point : currentPrice + BEBonus * Point,
            Digits
        );

        double currentSL = OrderStopLoss();
        double currentTP = OrderTakeProfit();
        bool shouldModify = false;

        if(type == OP_BUY)
            shouldModify = (currentTP > 0 || currentSL == 0 || newSL > currentSL + (Point / 2.0));
        else
            shouldModify = (currentTP > 0 || currentSL == 0 || newSL < currentSL - (Point / 2.0));

        if(!shouldModify)
            continue;

        ResetLastError();
        if(OrderModify(OrderTicket(), OrderOpenPrice(), newSL, 0, 0, clrBlue))
        {
            string typeStr = type == OP_BUY ? "BUY" : "SELL";
            Log("TrailingTP updated: Ticket=" + IntegerToString(OrderTicket()) +
                " Type=" + typeStr +
                " ProfitPoints=" + DoubleToString(profitPoints, 0) +
                " New SL=" + DoubleToString(newSL));
        }
        else
        {
            Log("ERROR: TrailingTP failed: Ticket=" + IntegerToString(OrderTicket()) +
                " Error=" + IntegerToString(GetLastError()));
        }
    }
}

bool IsWdOrder()
{
    // Only manage orders opened by this system.
    // ExecuteWdDecision uses comment format: "WD BUY" / "WD SELL".
    string c = OrderComment();
    if(StringLen(c) < 2)
        return false;
    return (StringFind(c, "WD ", 0) == 0);
}

void CheckCloseIfNoProfitAfterNCandles()
{
    if(!CloseIfNoProfitAfterNCandles_enabled)
        return;
    if(CloseIfNoProfitAfterNCandles <= 0)
        return;

    // Evaluate once per completed candle to avoid repeated close attempts per tick.
    static datetime lastCheckedBarTime = 0;
    if(Time[0] == lastCheckedBarTime)
        return;
    lastCheckedBarTime = Time[0];

    int closedCount = 0;
    int failedCount = 0;

    for(int i = OrdersTotal() - 1; i >= 0; i--)
    {
        if(!OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
            continue;
        if(OrderSymbol() != Symbol())
            continue;

        int type = OrderType();
        if(type != OP_BUY && type != OP_SELL)
            continue;
        if(!IsWdOrder())
            continue;

        // "No profit" means not positive including swap/commission.
        double netProfit = (OrderProfit() + OrderSwap() + OrderCommission());
        if(netProfit > 0.0)
            continue;

        int shift = iBarShift(Symbol(), Period(), OrderOpenTime(), false);
        if(shift < 0)
            continue;

        // Number of completed candles since open (approx): shift==0 means opened in current candle.
        if(shift < CloseIfNoProfitAfterNCandles)
            continue;

        RefreshRates();
        double closePrice = (type == OP_BUY) ? Bid : Ask;
        int ticket = OrderTicket();
        double lots = OrderLots();

        ResetLastError();
        if(OrderClose(ticket, lots, closePrice, slippage, clrNONE))
        {
            closedCount++;
            string dir = (type == OP_BUY) ? "BUY" : "SELL";
            Log("Closed (no profit after " + IntegerToString(CloseIfNoProfitAfterNCandles) +
                " candles) Ticket=" + IntegerToString(ticket) +
                " Type=" + dir +
                " BarsSinceOpen=" + IntegerToString(shift) +
                " Profit=" + DoubleToStr(netProfit, 2));
        }
        else
        {
            failedCount++;
            Log("ERROR: CloseIfNoProfitAfterNCandles failed Ticket=" + IntegerToString(ticket) +
                " Error=" + IntegerToString(GetLastError()));
        }
    }

    if(closedCount > 0 || failedCount > 0)
    {
        Log("CloseIfNoProfitAfterNCandles: closed=" + IntegerToString(closedCount) +
            " failed=" + IntegerToString(failedCount) +
            " N=" + IntegerToString(CloseIfNoProfitAfterNCandles));
    }
}

bool CheckWeakClosedOnFlip(string decision)
{
    // If we already have opposite WD trades open, do not open a new one.
    // Instead, close the worst-performing opposite order.
    // "Worst" = lowest (profit+swap+commission).

    int total = OrdersTotal();
    if(total < 2)
        return false;

    bool wantBuy = (decision == "BUY");
    int oppositeType = wantBuy ? OP_SELL : OP_BUY;

    if(weak_closed_on_flip_min_opp_enabled)
    {
        int howManyOppositeType = 0;
        for(int i = total - 1; i >= 0; i--)
        {
            if(!OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
                continue;
            if(OrderSymbol() != Symbol())
                continue;
            if(OrderType() != oppositeType)
                continue;

            howManyOppositeType++;
        }

        if(howManyOppositeType < weak_closed_on_flip_min_opp)
            return false;
    }

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
		        string wb = wantBuy ? "SELL" : "BUY";
                Log("Closed worst " + wb + " instead of opening " + decision + 
                      " Ticket=" + IntegerToString(worstTicket) + " Profit=" + DoubleToStr(worstProfit, 2));
                
                // closed worst
                return true;
            }
            else
            {
		        string wb = wantBuy ? "SELL" : "BUY";
                Log("ERROR: Failed to close worst " + wb + " Ticket=" + IntegerToString(worstTicket) +
                      " Error=" + IntegerToString(GetLastError()));
            }
        }
    }

    return false;
}

bool CheckPriceCondition(string &parts[], int partsCount, double currentPrice, string decision)
{
    // Check for condition (ABOVE/BELOW) and price
    if(partsCount >= 3)
    {
        int conditionIndex = 1;
        int priceIndex = 2;
        int ignoredAge = -1;

        if(partsCount >= 4 && TryExtractLineAge(parts[1], ignoredAge))
        {
            conditionIndex = 2;
            priceIndex = 3;
        }

        if(priceIndex >= partsCount)
            return true;

        string condition = parts[conditionIndex];
        double conditionPrice = StringToDouble(parts[priceIndex]);
        
        if(condition == "ABOVE" || condition == "BELOW")
        {
            if(condition == "ABOVE")
            {
                double priceWithTolerance = conditionPrice - OrderAboveOrBelowTolerance;
                if(currentPrice <= priceWithTolerance)
                {
                    Log("Skipping " + decision + " - Price " + DoubleToString(currentPrice, 2) + 
                        " not above " + DoubleToString(conditionPrice, 2) + 
                        " tolerance " + IntegerToString(OrderAboveOrBelowTolerance));
                    return false;
                }
                if(currentPrice >= conditionPrice + OrderAboveOrBelowGap)
                {
                    Log("Skipping " + decision + " - Price " + DoubleToString(currentPrice, 2) + 
                        " too high above " + DoubleToString(conditionPrice, 2) + 
                        " with gap " + IntegerToString(OrderAboveOrBelowGap));
                    return false;
		        }
            }
            else if(condition == "BELOW")
            {
                double priceWithTolerance = conditionPrice + OrderAboveOrBelowTolerance;
                if(currentPrice >= priceWithTolerance)
                {
                    Log("Skipping " + decision + " - Price " + DoubleToString(currentPrice, 2) + 
                        " not below " + DoubleToString(conditionPrice, 2) + 
                        " tolerance " + IntegerToString(OrderAboveOrBelowTolerance));
                    return false;
                }		
                if(currentPrice <= conditionPrice - OrderAboveOrBelowGap)
                {
                    Log("Skipping " + decision + " - Price " + DoubleToString(currentPrice, 2) + 
                        " too low below " + DoubleToString(conditionPrice, 2) + 
                        " with gap " + IntegerToString(OrderAboveOrBelowGap));
                    return false;
		        }
            }
        }
    }
    
    return true;
}

bool TryExtractLineAge(string token, int &age)
{
    age = -1;

    int openPos = StringFind(token, "(", 0);
    int closePos = StringFind(token, ")", openPos + 1);
    if(openPos < 0 || closePos <= openPos + 1)
        return false;

    string ageText = StringSubstr(token, openPos + 1, closePos - openPos - 1);
    if(StringLen(ageText) <= 0)
        return false;

    age = StrToInteger(ageText);
    return true;
}

// Decision format can be like "BUY SA2(3) ABOVE 21917.27", "BUY ABOVE 21917.27", or "SELL"
int ExecuteWdDecision(string decision)
{
    // Parse decision string
    string parts[];
    int partsCount = StringSplit(decision, ' ', parts);
    
    if(partsCount < 1)
        return 0;
    
    string orderTypeStr = parts[0];
    if(orderTypeStr != "BUY" && orderTypeStr != "SELL")
        return 0; 

    int lineAge = -1;
    bool hasLineAge = false;
    if(partsCount >= 2)
        hasLineAge = TryExtractLineAge(parts[1], lineAge); 

    if(MinLineAge_enabled && hasLineAge && lineAge < MinLineAge)
    {
        Log("Skipping " + decision + " - line age " + IntegerToString(lineAge) +
            " is below MinLineAge " + IntegerToString(MinLineAge));
        return 0;
    }
    
    bool isBuy = (orderTypeStr == "BUY");
    int cmd = isBuy ? OP_BUY : OP_SELL;
    double currentPrice = NormalizeDouble(isBuy ? Ask : Bid, Digits);

    if (OrderAboveOrBelow_enabled)
    {
        // Check price condition (ABOVE/BELOW)
        if(!CheckPriceCondition(parts, partsCount, currentPrice, decision))
            return 0;
    }
    
    if(HasSimilarOpenOrder_enabled && HasSimilarOpenOrder(cmd, currentPrice))
        return 0;

    if(ThirdOrderGap_enabled && HasSimilarOpenOrderThird(cmd, currentPrice))
        return 0;

    if (weak_closed_on_flip_enabled && CheckWeakClosedOnFlip(orderTypeStr))
        return 0;
    
    int stopLevelPoints = (int)MarketInfo(Symbol(), MODE_STOPLEVEL);
    int freezeLevelPoints = (int)MarketInfo(Symbol(), MODE_FREEZELEVEL);
    double minStopDistance = MathMax(stopLevelPoints, freezeLevelPoints) * Point;
    double slDist = MathMax(stopLoss * Point, minStopDistance);
    double tpDist = MathMax(takeProfit * Point, minStopDistance);
    
    double tp = NormalizeDouble(isBuy ? currentPrice + tpDist : currentPrice - tpDist, Digits);
    double sl = NormalizeDouble(isBuy ? currentPrice - slDist : currentPrice + slDist, Digits);
    double orderTP = TrailingTP_enabled ? 0 : tp;
    
    ResetLastError();
    int ticket = OrderSend(Symbol(), cmd, lotSize, currentPrice, slippage, sl, orderTP, 
                           "WD " + orderTypeStr, 0, 0, isBuy ? clrGreen : clrRed);
    
    if(ticket > 0)
    {
        Log("Order opened: " + decision + " Ticket=" + IntegerToString(ticket));

        if(SetAllOrdersSlToMaxSl_enabled)
                SetAllOrdersSlToMaxSl(cmd);
    }
    else
    {
        Log("ERROR: Order failed: " + decision + " Error=" + IntegerToString(GetLastError()) + 
              " Price=" + DoubleToString(currentPrice) + " SL=" + DoubleToString(sl) + " TP=" + DoubleToString(orderTP));
    }
    
    return ticket;
}
