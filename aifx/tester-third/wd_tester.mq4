
#property copyright "Copyright 2025"
#property link      ""
#property strict

string version = "1.0";

//----------------------------------------------------------------------- INPUTS

input bool show_lines = false;    
input double minDistance = 1500; // set to 0 to disable
input bool close_all_on_sl = false;
input bool close_opposite_on_flip = true;
input bool check_before_open = true;

// account-currency floating profit threshold to lock +10 points on all open positions
input double risk_bonus = 5;
// how many points to lock in once risk_bonus is exceeded
input double risk_bonus_sl = 2;

input double lotSize = 0.01;
input int takeProfit = 20000;
input int stopLoss = 10000;

//-----------------------------------------------------------------------

int slippage = 300;

// used by close_all_on_sl
datetime g_lastHistoryCheck = 0;

string WD_LINE_PREFIX = "WD_LINE_";
string WD_STATS_LABEL = "WD_STATS";

bool _ExtractBaseFromResult(string result, double &basePrice)
{
    basePrice = 0.0;
    if(result == "")
        return false;

    string parts[];
    int n = StringSplit(result, '|', parts);
    if(n <= 0)
        return false;

    for(int i = 0; i < n; i++)
    {
        string token = StringTrimLeft(StringTrimRight(parts[i]));
        if(StringFind(token, "BASE:") == 0)
        {
            string baseStr = StringTrimLeft(StringTrimRight(StringSubstr(token, 5)));
            basePrice = StrToDouble(baseStr);
            return (basePrice != 0.0);
        }
    }

    return false;
}

bool _ExtractCrossHeader(string result, string &firstLineId, string &direction)
{
    firstLineId = "";
    direction = "";
    if(result == "")
        return false;

    int pipePos = StringFind(result, "|");
    string header = pipePos >= 0 ? StringSubstr(result, 0, pipePos) : result;
    header = StringTrimLeft(StringTrimRight(header));

    if(StringFind(header, "CROSSED") != 0)
        return false;

    string tokens[];
    int nt = StringSplit(header, ' ', tokens);
    if(nt < 3)
        return false;

    // Format: CROSSED <IDs...> <UP|DOWN>
    firstLineId = StringTrimLeft(StringTrimRight(tokens[1]));
    direction = StringTrimLeft(StringTrimRight(tokens[nt - 1]));
    return (firstLineId != "" && (direction == "UP" || direction == "DOWN"));
}

bool _ExtractOffsetFromResult(string result, string key, double &offset)
{
    offset = 0.0;
    if(result == "")
        return false;

    string parts[];
    int n = StringSplit(result, '|', parts);
    if(n <= 0)
        return false;

    for(int i = 0; i < n; i++)
    {
        string token = StringTrimLeft(StringTrimRight(parts[i]));
        if(StringFind(token, key + ":") == 0)
        {
            string valStr = StringTrimLeft(StringTrimRight(StringSubstr(token, StringLen(key) + 1)));
            offset = StrToDouble(valStr);
            return true;
        }
    }
    return false;
}

bool CheckDecisionAgainstResultAndPrice(string decision, string result, string &reason)
{
    reason = "";

    string lineId = "";
    string dir = "";
    if(!_ExtractCrossHeader(result, lineId, dir))
    {
        reason = "result header is not CROSSED";
        return false;
    }

    // Validate BASE (detect stale/misaligned files).
    double base = 0.0;
    if(!_ExtractBaseFromResult(result, base))
    {
        reason = "result missing BASE";
        return false;
    }

    double tol = 5 * Point;
    // BASE comes from the last closed candle in the python pipeline.
    if(MathAbs(base - Close[1]) > tol)
    {
        reason = StringFormat("BASE mismatch (base=%.2f close1=%.*f)", base, Digits, Close[1]);
        return false;
    }

    // Validate decision matches result direction + line family.
    if(decision == "BUY")
    {
        if(dir != "UP")
        {
            reason = "BUY but result direction is not UP";
            return false;
        }
        if(StringLen(lineId) < 1 || StringSubstr(lineId, 0, 1) != "A")
        {
            reason = "BUY but crossed line is not A*";
            return false;
        }

        double d0 = 0.0;
        bool hasD0 = _ExtractOffsetFromResult(result, "D0", d0);

        // Gap/price validation: current price must still be on the valid side.
        if(hasD0)
        {
            double d0Price = base + d0;
            double currentPrice = (Ask + Bid) / 2.0;
            if(currentPrice < d0Price - tol)
            {
                reason = StringFormat("BUY invalidated by gap: current below D0 (current=%.*f D0=%.*f)", Digits, currentPrice, Digits, d0Price);
                return false;
            }
        }

        // Original decisioner rule.
        if(hasD0 && d0 > 0.0)
        {
            reason = "BUY blocked: base below D0 (D0 offset > 0)";
            return false;
        }
    }
    else if(decision == "SELL")
    {
        if(dir != "DOWN")
        {
            reason = "SELL but result direction is not DOWN";
            return false;
        }
        if(StringLen(lineId) < 1 || StringSubstr(lineId, 0, 1) != "D")
        {
            reason = "SELL but crossed line is not D*";
            return false;
        }

        double a0 = 0.0;
        bool hasA0 = _ExtractOffsetFromResult(result, "A0", a0);

        // Gap/price validation: current price must still be on the valid side.
        if(hasA0)
        {
            double a0Price = base + a0;
            double currentPrice = (Ask + Bid) / 2.0;
            if(currentPrice > a0Price + tol)
            {
                reason = StringFormat("SELL invalidated by gap: current above A0 (current=%.*f A0=%.*f)", Digits, currentPrice, Digits, a0Price);
                return false;
            }
        }

        // Original decisioner rule.
        if(hasA0 && a0 < 0.0)
        {
            reason = "SELL blocked: base above A0 (A0 offset < 0)";
            return false;
        }
    }

    return true;
}

string ReadAllText(string filepath)
{
    int fileHandle = FileOpen(filepath, FILE_READ|FILE_TXT);
    if(fileHandle == INVALID_HANDLE)
    {
        int err = GetLastError();
        Print("Failed to open file: ", filepath, " Error: ", err);
        return "";
    }

    string content = "";
    while(!FileIsEnding(fileHandle))
    {
        content += FileReadString(fileHandle);
    }
    FileClose(fileHandle);

    content = StringTrimLeft(content);
    content = StringTrimRight(content);
    return content;
}

void DeleteWdLines()
{
    int total = ObjectsTotal(0, 0, -1);
    for(int i = total - 1; i >= 0; i--)
    {
        string name = ObjectName(0, i);
        if(StringFind(name, WD_LINE_PREFIX) == 0)
        {
            ObjectDelete(0, name);
        }
    }
}

void UpsertHLine(string name, double price, color lineColor, int lineStyle)
{
    if(ObjectFind(0, name) < 0)
    {
        ObjectCreate(0, name, OBJ_HLINE, 0, 0, price);
        ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
        ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
        ObjectSetInteger(0, name, OBJPROP_WIDTH, 1);
    }
    else
    {
        ObjectSetDouble(0, name, OBJPROP_PRICE, price);
    }

    ObjectSetInteger(0, name, OBJPROP_COLOR, lineColor);
    ObjectSetInteger(0, name, OBJPROP_STYLE, lineStyle);
}

void UpsertTrendLine(string name, datetime time0, double price0, datetime time1, double price1, color lineColor, int lineStyle)
{
    if(ObjectFind(0, name) < 0)
    {
        ObjectCreate(0, name, OBJ_TREND, 0, time1, price1, time0, price0);
        ObjectSetInteger(0, name, OBJPROP_SELECTABLE, true);
        ObjectSetInteger(0, name, OBJPROP_HIDDEN, false);
        ObjectSetInteger(0, name, OBJPROP_WIDTH, 1);
        ObjectSetInteger(0, name, OBJPROP_RAY_RIGHT, false);
        ObjectSetInteger(0, name, OBJPROP_RAY_LEFT, false);
    }
    else
    {
        ObjectMove(0, name, 0, time1, price1);
        ObjectMove(0, name, 1, time0, price0);
    }

    ObjectSetInteger(0, name, OBJPROP_COLOR, lineColor);
    ObjectSetInteger(0, name, OBJPROP_STYLE, lineStyle);
    ObjectSetInteger(0, name, OBJPROP_RAY_RIGHT, false);
    ObjectSetInteger(0, name, OBJPROP_RAY_LEFT, false);
}

void DrawLinesFromResult(string result)
{
    if(result == "")
        return;

    string parts[];
    int n = StringSplit(result, '|', parts);
    if(n <= 0)
        return;

    double basePrice = Close[0];
    double absSlope = 0.0;

    for(int i = 0; i < n; i++)
    {
        parts[i] = StringTrimLeft(parts[i]);
        parts[i] = StringTrimRight(parts[i]);
        if(StringFind(parts[i], "BASE:") == 0)
        {
            string baseStr = StringSubstr(parts[i], 5);
            baseStr = StringTrimLeft(baseStr);
            baseStr = StringTrimRight(baseStr);
            basePrice = StrToDouble(baseStr);
            break;
        }
    }

    for(int i = 0; i < n; i++)
    {
        parts[i] = StringTrimLeft(parts[i]);
        parts[i] = StringTrimRight(parts[i]);
        if(StringFind(parts[i], "SLOPE:") == 0)
        {
            string slopeStr = StringSubstr(parts[i], 6);
            slopeStr = StringTrimLeft(slopeStr);
            slopeStr = StringTrimRight(slopeStr);
            absSlope = MathAbs(StrToDouble(slopeStr));
            break;
        }
    }

    for(int i = 0; i < n; i++)
    {
        string token = parts[i];
        token = StringTrimLeft(token);
        token = StringTrimRight(token);

        if(token == "" || token == "NONE")
            continue;
        if(StringFind(token, "CROSSED ") == 0)
            continue;
        if(StringFind(token, "SLOPE:") == 0)
            continue;
        if(StringFind(token, "BASE:") == 0)
            continue;

        int colonPos = StringFind(token, ":");
        if(colonPos <= 0)
            continue;

        string id = StringSubstr(token, 0, colonPos);
        string offsetStr = StringSubstr(token, colonPos + 1);
        id = StringTrimLeft(id);
        id = StringTrimRight(id);
        offsetStr = StringTrimLeft(offsetStr);
        offsetStr = StringTrimRight(offsetStr);

        if(StringLen(id) <= 0)
            continue;
        if(StringLen(offsetStr) <= 0)
            continue;

        double offset = StrToDouble(offsetStr);
        double price = basePrice + offset;
        // Print("id: " + id + " price: " + DoubleToStr(price));

        color c = clrSilver;
        bool isA = (StringSubstr(id, 0, 1) == "A");
        if(isA)
            c = clrGreen;
        else if(StringSubstr(id, 0, 1) == "D")
            c = clrRed;

        // A0/D0 are main lines: solid. The rest: dashed.
        int lineStyle = (id == "A0" || id == "D0") ? STYLE_SOLID : STYLE_DASH;

        if(absSlope > 0.0)
        {
            double slopeSigned = isA ? absSlope : -absSlope;
            datetime t0 = Time[0];

            int spanBars = 300;
            double pAt0 = price;
            
            // IMPORTANT: spanBars means real candles (bar shift), not time periods.
            // Using time math breaks over weekends/gaps.
            int leftShift = spanBars;
            if(Bars <= leftShift)
                leftShift = Bars - 1;
            if(leftShift < 1)
                leftShift = 1;
            datetime tLeft = Time[leftShift];
            double pLeft = pAt0 - slopeSigned * spanBars;

            datetime tRight = t0 + (Period() * 60 * 1);
            double pRight = pAt0 + slopeSigned * 1;
            UpsertTrendLine(WD_LINE_PREFIX + id, tRight, pRight, tLeft, pLeft, c, lineStyle);
        }
        else
        {
            UpsertHLine(WD_LINE_PREFIX + id, price, c, lineStyle);
        }
    }
}

void ApplyBlackOnWhiteTheme()
{
    long chartId = 0;

    ChartSetInteger(chartId, CHART_MODE, CHART_CANDLES);

    ChartSetInteger(chartId, CHART_COLOR_BACKGROUND, clrWhite);
    ChartSetInteger(chartId, CHART_COLOR_FOREGROUND, clrBlack);
    ChartSetInteger(chartId, CHART_COLOR_GRID, clrSilver);
    ChartSetInteger(chartId, CHART_COLOR_VOLUME, clrBlack);

    ChartSetInteger(chartId, CHART_COLOR_CHART_UP, clrBlack);
    ChartSetInteger(chartId, CHART_COLOR_CHART_DOWN, clrBlack);
    ChartSetInteger(chartId, CHART_COLOR_CANDLE_BULL, clrWhite);
    ChartSetInteger(chartId, CHART_COLOR_CANDLE_BEAR, clrBlack);
    
    ChartRedraw(chartId);
}

bool GetClosestOrderForSymbol(string symbol, double referencePrice, double &closestPrice, double &closestDistance)
{
    closestPrice = 0.0;
    closestDistance = 0.0;

    double bestDistance = -1.0;
    double bestPrice = 0.0;

    int total = OrdersTotal();
    for(int i = 0; i < total; i++)
    {
        if(!OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
            continue;
        if(OrderSymbol() != symbol)
            continue;

        int type = OrderType();
        if(type != OP_BUY && type != OP_SELL && type != OP_BUYLIMIT && type != OP_SELLLIMIT && type != OP_BUYSTOP && type != OP_SELLSTOP)
            continue;

        double price = OrderOpenPrice();
        double distance = MathAbs(referencePrice - price);

        if(bestDistance < 0.0 || distance < bestDistance)
        {
            bestDistance = distance;
            bestPrice = price;
        }
    }

    if(bestDistance < 0.0)
        return false;

    closestPrice = bestPrice;
    closestDistance = bestDistance;
    return true;
}

bool IsOrderClosedByStopLoss(int type, double stopLossPrice, double closePrice)
{
    if(stopLossPrice <= 0.0)
        return false;

    double tol = 2 * Point;
    if(type == OP_BUY)
        return (closePrice <= stopLossPrice + tol);
    if(type == OP_SELL)
        return (closePrice >= stopLossPrice - tol);

    return false;
}

bool DetectNewStopLossClose(datetime &sinceTime, int &slTicket)
{
    slTicket = -1;
    datetime newest = sinceTime;
    bool found = false;

    int total = OrdersHistoryTotal();
    for(int i = total - 1; i >= 0; i--)
    {
        if(!OrderSelect(i, SELECT_BY_POS, MODE_HISTORY))
            continue;

        datetime ct = OrderCloseTime();
        if(ct <= 0)
            continue;
        if(ct <= sinceTime)
            continue;

        if(ct > newest)
            newest = ct;

        int type = OrderType();
        if(type != OP_BUY && type != OP_SELL)
            continue;

        double sl = OrderStopLoss();
        double cp = OrderClosePrice();
        if(IsOrderClosedByStopLoss(type, sl, cp))
        {
            slTicket = OrderTicket();
            found = true;
            // keep scanning to advance newest
        }
    }

    sinceTime = newest;
    return found;
}

bool IsBuySideOrderType(int type)
{
    return (type == OP_BUY || type == OP_BUYLIMIT || type == OP_BUYSTOP);
}

bool IsSellSideOrderType(int type)
{
    return (type == OP_SELL || type == OP_SELLLIMIT || type == OP_SELLSTOP);
}

bool HasOrdersForSymbolSide(string symbol, bool sellSide)
{
    int total = OrdersTotal();
    for(int i = 0; i < total; i++)
    {
        if(!OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
            continue;
        if(OrderSymbol() != symbol)
            continue;

        int type = OrderType();
        if(sellSide && IsSellSideOrderType(type))
            return true;
        if(!sellSide && IsBuySideOrderType(type))
            return true;
    }
    return false;
}

double GetTotalOpenPositionsProfit()
{
    double totalProfit = 0.0;

    int total = OrdersTotal();
    for(int i = 0; i < total; i++)
    {
        if(!OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
            continue;

        int type = OrderType();
        if(type != OP_BUY && type != OP_SELL)
            continue;

        totalProfit += (OrderProfit() + OrderSwap() + OrderCommission());
    }

    return totalProfit;
}

bool TrySetOrderStopLossToBonus(int ticket, double bonusPoints)
{
    if(!OrderSelect(ticket, SELECT_BY_TICKET, MODE_TRADES))
        return false;

    int type = OrderType();
    if(type != OP_BUY && type != OP_SELL)
        return false;

    string sym = OrderSymbol();
    double bid = MarketInfo(sym, MODE_BID);
    double ask = MarketInfo(sym, MODE_ASK);
    int digits = (int)MarketInfo(sym, MODE_DIGITS);
    double point = MarketInfo(sym, MODE_POINT);

    int stopLevelPoints = (int)MarketInfo(sym, MODE_STOPLEVEL);
    int freezeLevelPoints = (int)MarketInfo(sym, MODE_FREEZELEVEL);
    double minStopDistance = MathMax(stopLevelPoints, freezeLevelPoints) * point;

    double desiredSL = 0.0;
    if(type == OP_BUY)
        desiredSL = NormalizeDouble(OrderOpenPrice() + bonusPoints * point, digits);
    else
        desiredSL = NormalizeDouble(OrderOpenPrice() - bonusPoints * point, digits);

    // Only tighten (never loosen) SL.
    double currentSL = OrderStopLoss();
    if(type == OP_BUY && currentSL > 0.0 && currentSL >= desiredSL)
        return true;
    if(type == OP_SELL && currentSL > 0.0 && currentSL <= desiredSL)
        return true;

    // Ensure broker stop/freeze distance allows this SL.
    if(type == OP_BUY)
    {
        if(bid - desiredSL < minStopDistance)
            return false;
    }
    else
    {
        if(desiredSL - ask < minStopDistance)
            return false;
    }

    ResetLastError();
    bool ok = OrderModify(ticket, OrderOpenPrice(), desiredSL, OrderTakeProfit(), 0, clrNONE);
    if(!ok)
    {
        int err = GetLastError();
        PrintFormat(
            "Failed to set bonus SL. ticket=%d sym=%s type=%d desiredSL=%.*f err=%d",
            ticket,
            sym,
            type,
            digits,
            desiredSL,
            err
        );
        return false;
    }

    return true;
}

bool TrySetOrderStopLossToPrice(int ticket, double desiredSL)
{
    if(!OrderSelect(ticket, SELECT_BY_TICKET, MODE_TRADES))
        return false;

    int type = OrderType();
    if(type != OP_BUY && type != OP_SELL)
        return false;

    string sym = OrderSymbol();
    double bid = MarketInfo(sym, MODE_BID);
    double ask = MarketInfo(sym, MODE_ASK);
    int digits = (int)MarketInfo(sym, MODE_DIGITS);
    double point = MarketInfo(sym, MODE_POINT);

    desiredSL = NormalizeDouble(desiredSL, digits);

    // Only tighten (never loosen) SL.
    double currentSL = OrderStopLoss();
    if(type == OP_BUY && currentSL > 0.0 && currentSL >= desiredSL)
        return true;
    if(type == OP_SELL && currentSL > 0.0 && currentSL <= desiredSL)
        return true;

    int stopLevelPoints = (int)MarketInfo(sym, MODE_STOPLEVEL);
    int freezeLevelPoints = (int)MarketInfo(sym, MODE_FREEZELEVEL);
    double minStopDistance = MathMax(stopLevelPoints, freezeLevelPoints) * point;

    // Ensure broker stop/freeze distance allows this SL.
    if(type == OP_BUY)
    {
        if(bid - desiredSL < minStopDistance)
            return false;
    }
    else
    {
        if(desiredSL - ask < minStopDistance)
            return false;
    }

    ResetLastError();
    bool ok = OrderModify(ticket, OrderOpenPrice(), desiredSL, OrderTakeProfit(), 0, clrNONE);
    if(!ok)
    {
        int err = GetLastError();
        PrintFormat(
            "Failed to set basket bonus SL. ticket=%d sym=%s type=%d desiredSL=%.*f err=%d",
            ticket,
            sym,
            type,
            digits,
            desiredSL,
            err
        );
        return false;
    }

    return true;
}

bool GetWdTesterBasketAvgOpenPriceForChartSymbol(bool buySide, double &avgOpenPrice, double &totalLots)
{
    avgOpenPrice = 0.0;
    totalLots = 0.0;

    double weighted = 0.0;

    int total = OrdersTotal();
    for(int i = 0; i < total; i++)
    {
        if(!OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
            continue;

        if(OrderSymbol() != Symbol())
            continue;

        int type = OrderType();
        if(buySide && type != OP_BUY)
            continue;
        if(!buySide && type != OP_SELL)
            continue;

        string c = OrderComment();
        if(StringFind(c, "WD Tester") != 0)
            continue;

        double lots = OrderLots();
        totalLots += lots;
        weighted += lots * OrderOpenPrice();
    }

    if(totalLots <= 0.0)
        return false;

    avgOpenPrice = weighted / totalLots;
    return true;
}

void ApplyRiskBonusProtection()
{
    if(risk_bonus <= 0.0)
        return;

    int posCount = 0;
    double posLots = 0.0;
    double totalProfit = 0.0;
    GetWdTesterOpenStatsForChartSymbol(posCount, posLots, totalProfit);

    if(totalProfit <= risk_bonus)
        return;

    // Once total floating profit exceeds risk_bonus, lock risk_bonus_sl points using ONE SL price for the whole basket.
    // (Same SL price for all orders, per side.)

    double buyAvg = 0.0, buyLots = 0.0;
    bool hasBuy = GetWdTesterBasketAvgOpenPriceForChartSymbol(true, buyAvg, buyLots);
    if(hasBuy)
    {
        double desiredBuySL = buyAvg + (risk_bonus_sl * Point);

        int total = OrdersTotal();
        for(int i = total - 1; i >= 0; i--)
        {
            if(!OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
                continue;
            if(OrderSymbol() != Symbol())
                continue;
            if(OrderType() != OP_BUY)
                continue;
            if(StringFind(OrderComment(), "WD Tester") != 0)
                continue;

            TrySetOrderStopLossToPrice(OrderTicket(), desiredBuySL);
        }
    }

    double sellAvg = 0.0, sellLots = 0.0;
    bool hasSell = GetWdTesterBasketAvgOpenPriceForChartSymbol(false, sellAvg, sellLots);
    if(hasSell)
    {
        double desiredSellSL = sellAvg - (risk_bonus_sl * Point);

        int total = OrdersTotal();
        for(int i = total - 1; i >= 0; i--)
        {
            if(!OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
                continue;
            if(OrderSymbol() != Symbol())
                continue;
            if(OrderType() != OP_SELL)
                continue;
            if(StringFind(OrderComment(), "WD Tester") != 0)
                continue;

            TrySetOrderStopLossToPrice(OrderTicket(), desiredSellSL);
        }
    }
}

void GetWdTesterOpenStatsForChartSymbol(int &positionsCount, double &totalLots, double &totalProfit)
{
    positionsCount = 0;
    totalLots = 0.0;
    totalProfit = 0.0;

    int total = OrdersTotal();
    for(int i = 0; i < total; i++)
    {
        if(!OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
            continue;

        if(OrderSymbol() != Symbol())
            continue;

        int type = OrderType();
        if(type != OP_BUY && type != OP_SELL)
            continue;

        string c = OrderComment();
        if(StringFind(c, "WD Tester") != 0)
            continue;

        positionsCount++;
        totalLots += OrderLots();
        totalProfit += (OrderProfit() + OrderSwap() + OrderCommission());
    }
}

void UpsertTesterStatsLabel(string text)
{
    if(ObjectFind(0, WD_STATS_LABEL) < 0)
    {
        ObjectCreate(0, WD_STATS_LABEL, OBJ_LABEL, 0, 0, 0);
        ObjectSetInteger(0, WD_STATS_LABEL, OBJPROP_CORNER, CORNER_LEFT_UPPER);
        ObjectSetInteger(0, WD_STATS_LABEL, OBJPROP_XDISTANCE, 10);
        ObjectSetInteger(0, WD_STATS_LABEL, OBJPROP_YDISTANCE, 10);
        ObjectSetInteger(0, WD_STATS_LABEL, OBJPROP_BACK, false);
        ObjectSetInteger(0, WD_STATS_LABEL, OBJPROP_SELECTABLE, false);
        ObjectSetInteger(0, WD_STATS_LABEL, OBJPROP_HIDDEN, true);
        ObjectSetInteger(0, WD_STATS_LABEL, OBJPROP_FONTSIZE, 10);
        ObjectSetString(0, WD_STATS_LABEL, OBJPROP_FONT, "Consolas");
        ObjectSetInteger(0, WD_STATS_LABEL, OBJPROP_COLOR, clrBlack);
    }

    ObjectSetString(0, WD_STATS_LABEL, OBJPROP_TEXT, text);
    ChartRedraw(0);
}

void DeleteTesterStatsLabel()
{
    if(ObjectFind(0, WD_STATS_LABEL) >= 0)
        ObjectDelete(0, WD_STATS_LABEL);
}

void UpdateTesterStatsOverlay()
{
    // Only show in Strategy Tester (visual mode uses a real chart; non-visual/optimization has no visible chart anyway).
    if(!IsTesting() && !IsVisualMode())
        return;

    int cnt = 0;
    double lots = 0.0;
    double profit = 0.0;
    GetWdTesterOpenStatsForChartSymbol(cnt, lots, profit);

    string text = "WD Tester\n";
    text += "Open positions: " + IntegerToString(cnt) + " (Lots: " + DoubleToStr(lots, 2) + ")\n";
    text += "Open profit: " + DoubleToStr(profit, 2);

    UpsertTesterStatsLabel(text);
}

void CloseOrdersForSymbolSide(string symbol, bool sellSide)
{
    RefreshRates();

    int total = OrdersTotal();
    for(int i = total - 1; i >= 0; i--)
    {
        if(!OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
            continue;
        if(OrderSymbol() != symbol)
            continue;

        int type = OrderType();
        if(sellSide && !IsSellSideOrderType(type))
            continue;
        if(!sellSide && !IsBuySideOrderType(type))
            continue;

        int ticket = OrderTicket();
        double lots = OrderLots();

        bool ok = false;
        ResetLastError();

        if(type == OP_BUY)
            ok = OrderClose(ticket, lots, Bid, 300, clrWhite);
        else if(type == OP_SELL)
            ok = OrderClose(ticket, lots, Ask, 300, clrWhite);
        else
            ok = OrderDelete(ticket);

        if(!ok)
        {
            int err = GetLastError();
            PrintFormat("Failed to close/delete order. ticket=%d type=%d err=%d", ticket, type, err);
        }
    }
}

void CloseAllOrders()
{
    RefreshRates();

    int total = OrdersTotal();
    for(int i = total - 1; i >= 0; i--)
    {
        if(!OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
            continue;

        int type = OrderType();
        int ticket = OrderTicket();
        double lots = OrderLots();

        bool ok = false;
        ResetLastError();

        if(type == OP_BUY)
            ok = OrderClose(ticket, lots, Bid, 300, clrWhite);
        else if(type == OP_SELL)
            ok = OrderClose(ticket, lots, Ask, 300, clrWhite);
        else
            ok = OrderDelete(ticket);

        if(!ok)
        {
            int err = GetLastError();
            PrintFormat("Failed to close/delete order. ticket=%d type=%d err=%d", ticket, type, err);
        }
    }
}

int OnInit()
{   
    Print("version: " + version);
    Print("show_lines: ", show_lines);
    ApplyBlackOnWhiteTheme();

    // Create stats overlay early so it is visible immediately in visual tester.
    UpdateTesterStatsOverlay();

    g_lastHistoryCheck = TimeCurrent();

    return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
    DeleteTesterStatsLabel();
}

void OnTick()
{
    RefreshRates();

    UpdateTesterStatsOverlay();

    ApplyRiskBonusProtection();

    int slTicket = -1;
    if(close_all_on_sl && DetectNewStopLossClose(g_lastHistoryCheck, slTicket))
    {
        PrintFormat("Detected SL close (ticket=%d). Closing all orders.", slTicket);
        CloseAllOrders();
        return;
    }

    datetime currentTime = Time[0];
    string timeStr = TimeToString(currentTime, TIME_DATE|TIME_MINUTES);
    StringReplace(timeStr, "2025", "25");
    StringReplace(timeStr, "2026", "26");
    StringReplace(timeStr, ".", "-");
    StringReplace(timeStr, ":", "-");
    StringReplace(timeStr, " ", "-");

    string decision_filename = "wd_tester/" + timeStr + "_decision.txt";
    string decision = ReadAllText(decision_filename);
    Print("Decision file content: ", decision);

    string result_filename = "wd_tester/" + timeStr + "_result.txt";
    string result = ReadAllText(result_filename);
    Print("Result file content: ", result);

    if(check_before_open && (decision == "BUY" || decision == "SELL"))
    {
        string reason = "";
        if(!CheckDecisionAgainstResultAndPrice(decision, result, reason))
        {
            PrintFormat("Skipping %s: check_before_open failed: %s", decision, reason);
            return;
        }
    }

    if (show_lines == true)
    {
        DeleteWdLines();
        DrawLinesFromResult(result);
    }
    else
    {
        DeleteWdLines();
    }

    // get price of closest order and do not open new one if current price is closer than 150
    double closestPrice = 0.0;
    double closestDistance = 0.0;
    double currentPrice = (Ask + Bid) / 2.0;

    bool hasClosest = GetClosestOrderForSymbol(Symbol(), currentPrice, closestPrice, closestDistance);


    if(decision == "BUY" || decision == "SELL")
    {
        if(close_opposite_on_flip && decision == "BUY" && HasOrdersForSymbolSide(Symbol(), true))
        {
            Print("BUY signal while SELL orders exist: closing SELL side and skipping.");
            CloseOrdersForSymbolSide(Symbol(), true);
            return;
        }
        if(close_opposite_on_flip && decision == "SELL" && HasOrdersForSymbolSide(Symbol(), false))
        {
            Print("SELL signal while BUY orders exist: closing BUY side and skipping.");
            CloseOrdersForSymbolSide(Symbol(), false);
            return;
        }

        if(minDistance > 0.0 && hasClosest && closestDistance < (minDistance * Point))
        {
            PrintFormat(
                "Skipping new order: closest existing order is %.0f points away (threshold=%.0f). current=%.*f closest=%.*f",
                closestDistance / Point, 
                minDistance,
                Digits, currentPrice,
                Digits, closestPrice
            );
            return;
        }

        
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
