#ifndef WD_TESTER_UI_MQH
#define WD_TESTER_UI_MQH

#define WD_ARROW_BUY 1
#define WD_ARROW_SELL 2
#define WD_ARROW_TP 3
#define WD_ARROW_SL 4
#define WD_ARROW_CLOSE 5

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

void DeleteCustomArrows()
{
    int deleted = 0;
    int total = ObjectsTotal(0, 0, -1);
    for(int i = total - 1; i >= 0; i--)
    {
        string name = ObjectName(0, i);
        if(StringFind(name, WD_CUSTOM_ARROW_PREFIX) == 0)
        {
            ObjectDelete(0, name);
            deleted++;
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

    datetime tBegin = time0;
    double pBegin = price0;
    datetime tEnd = time1;
    double pEnd = price1;
    if(time1 < time0)
    {
        tBegin = time1;
        pBegin = price1;
        tEnd = time0;
        pEnd = price0;
    }

    int secondsPerBar = (int)(Period() * 60);
    if(secondsPerBar <= 0)
        secondsPerBar = 60;
    int padSeconds = secondsPerBar * 5;

    datetime tLabelBegin = tBegin - padSeconds;
    datetime tLabelEnd = tEnd + padSeconds;

    string beginLabelName = name + "_BEGIN";
    string endLabelName = name + "_END";

    if(ObjectFind(0, beginLabelName) < 0)
    {
        ObjectCreate(0, beginLabelName, OBJ_TEXT, 0, tLabelBegin, pBegin);
        ObjectSetInteger(0, beginLabelName, OBJPROP_BACK, false);
        ObjectSetInteger(0, beginLabelName, OBJPROP_SELECTABLE, false);
        ObjectSetInteger(0, beginLabelName, OBJPROP_HIDDEN, true);
        ObjectSetInteger(0, beginLabelName, OBJPROP_FONTSIZE, 8);
        ObjectSetString(0, beginLabelName, OBJPROP_FONT, "Consolas");
    }
    else
    {
        ObjectMove(0, beginLabelName, 0, tLabelBegin, pBegin);
    }

    ObjectSetInteger(0, beginLabelName, OBJPROP_COLOR, lineColor);
    ObjectSetString(0, beginLabelName, OBJPROP_TEXT, name);

    if(ObjectFind(0, endLabelName) < 0)
    {
        ObjectCreate(0, endLabelName, OBJ_TEXT, 0, tLabelEnd, pEnd);
        ObjectSetInteger(0, endLabelName, OBJPROP_BACK, false);
        ObjectSetInteger(0, endLabelName, OBJPROP_SELECTABLE, false);
        ObjectSetInteger(0, endLabelName, OBJPROP_HIDDEN, true);
        ObjectSetInteger(0, endLabelName, OBJPROP_FONTSIZE, 8);
        ObjectSetString(0, endLabelName, OBJPROP_FONT, "Consolas");
    }
    else
    {
        ObjectMove(0, endLabelName, 0, tLabelEnd, pEnd);
    }

    ObjectSetInteger(0, endLabelName, OBJPROP_COLOR, lineColor);
    ObjectSetString(0, endLabelName, OBJPROP_TEXT, name);
}

void DrawLinesFromResult()
{
    if(show_lines == false)
        return;

    if(g_result == "EMPTY")
        return;

    g_numDscAbove = 0;
    g_numAscBelow = 0;

    string parts[];
    int n = StringSplit(g_result, '|', parts);
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

    int total = ObjectsTotal(0, 0, -1);
    for(int i = 0; i < total; i++)
    {
        string name = ObjectName(0, i);
        if(StringFind(name, WD_LINE_PREFIX) == 0)
        {
            ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
            string beginLabelName = name + "_BEGIN";
            string endLabelName = name + "_END";
            if(ObjectFind(0, beginLabelName) >= 0)
                ObjectSetInteger(0, beginLabelName, OBJPROP_HIDDEN, true);
            if(ObjectFind(0, endLabelName) >= 0)
                ObjectSetInteger(0, endLabelName, OBJPROP_HIDDEN, true);
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

        if(StringFind(id, "D") != -1 && offset > 0)
            g_numDscAbove++;
        else if(StringFind(id, "A") != -1 && offset < 0)
            g_numAscBelow++;

        color c = clrSilver;
        int lineAge = -1;
        bool hasLineAge = TryExtractLineAge(id, lineAge);

        bool isA = (StringFind(id, "A") != -1);
        bool isD = (StringFind(id, "D") != -1);

        if(isA)
            c = clrGreen;
        else if(isD)
            c = clrRed;

        if(MinLineAge_enabled && hasLineAge && lineAge < MinLineAge)
            c = clrGray;

        int lineStyle = (id == "AM" || id == "DM") ? STYLE_SOLID : STYLE_DASH;

        if(absSlope > 0.0)
        {
            double slopeSigned = isA ? absSlope : -absSlope;
            datetime t0 = Time[0];

            int spanBars = 300;
            double pAt0 = price;

            int leftShift = spanBars;
            if(Bars <= leftShift)
                leftShift = Bars - 1;
            if(leftShift < 1)
                leftShift = 1;
            datetime tLeft = Time[leftShift];
            double pLeft = pAt0 - slopeSigned * spanBars;

            datetime tRight = t0 + (Period() * 60 * 1);
            double pRight = pAt0 - slopeSigned * 1;
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
    ChartSetInteger(chartId, CHART_SCALE, 2);

    ChartRedraw(chartId);
}

void GetWdTesterOpenStatsForChartSymbol(int &positionsCount, int &buyCount, int &sellCount,
    double &totalLots, double &totalProfit)
{
    positionsCount = 0;
    buyCount = 0;
    sellCount = 0;
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

        if(type == OP_BUY)
            buyCount++;
        else if(type == OP_SELL)
            sellCount++;

        positionsCount++;
        totalLots += OrderLots();
        totalProfit += (OrderProfit() + OrderSwap() + OrderCommission());
    }
}

void UpsertTesterStatsLabel(string text)
{
    if(ObjectFind(0, WD_STATS_LABEL) >= 0)
        ObjectDelete(0, WD_STATS_LABEL);

    string lines[];
    int n = StringSplit(text, '\n', lines);
    if(n <= 0)
    {
        ArrayResize(lines, 1);
        lines[0] = text;
        n = 1;
    }

    int baseX = 5;
    int baseY = 20;
    int fontSize = 9;
    int lineHeight = fontSize + 7;

    for(int i = 0; i < n; i++)
    {
        StringReplace(lines[i], "\r", "");
        string lineText = (lines[i] == "") ? " " : lines[i];

        string name = WD_STATS_LABEL + "_" + IntegerToString(i);
        if(ObjectFind(0, name) < 0)
        {
            ObjectCreate(0, name, OBJ_LABEL, 0, 0, 0);
            ObjectSetInteger(0, name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
            ObjectSetInteger(0, name, OBJPROP_BACK, false);
            ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
            ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
            ObjectSetInteger(0, name, OBJPROP_FONTSIZE, fontSize);
            ObjectSetString(0, name, OBJPROP_FONT, "Consolas");
            ObjectSetInteger(0, name, OBJPROP_COLOR, clrBlack);
        }

        ObjectSetInteger(0, name, OBJPROP_XDISTANCE, baseX);
        ObjectSetInteger(0, name, OBJPROP_YDISTANCE, baseY + i * lineHeight);
        ObjectSetString(0, name, OBJPROP_TEXT, lineText);
    }

    int total = ObjectsTotal(0, 0, -1);
    for(int j = total - 1; j >= 0; j--)
    {
        string objName = ObjectName(0, j);
        if(StringFind(objName, WD_STATS_LABEL + "_") != 0)
            continue;

        int idx = StrToInteger(StringSubstr(objName, StringLen(WD_STATS_LABEL) + 1));
        if(idx >= n)
            ObjectDelete(0, objName);
    }

    ChartRedraw(0);
}

void DeleteTesterStatsLabel()
{
    if(ObjectFind(0, WD_STATS_LABEL) >= 0)
        ObjectDelete(0, WD_STATS_LABEL);

    int total = ObjectsTotal(0, 0, -1);
    for(int i = total - 1; i >= 0; i--)
    {
        string name = ObjectName(0, i);
        if(StringFind(name, WD_STATS_LABEL + "_") == 0)
            ObjectDelete(0, name);
    }
}

void UpdateTesterStatsOverlay()
{
    if(!IsTesting() && !IsVisualMode())
        return;

    GetWdTesterOpenStatsForChartSymbol(g_cnt, g_buyCnt, g_sellCnt, g_lots, g_profit);

    string text = "WD Tester\n";
    text += "File: " + g_tester_filename + " (-15m)\n";
    text += "Open positions: " + IntegerToString(g_cnt) +
        " (BUY: " + IntegerToString(g_buyCnt) + ", SELL: " + IntegerToString(g_sellCnt) +
        ", Lots: " + DoubleToStr(g_lots, 2) + ")\n";
    text += "Open profit: " + DoubleToStr(g_profit, 2);
    text += "\nD above: " + IntegerToString(g_numDscAbove) + " | A below: " + IntegerToString(g_numAscBelow);

    UpsertTesterStatsLabel(text);
}

bool IsArrowObjectType(int objectType)
{
    return objectType == OBJ_ARROW ||
        objectType == OBJ_TRIANGLE ||
        objectType == OBJ_ARROW_BUY ||
        objectType == OBJ_ARROW_SELL ||
        objectType == OBJ_ARROW_STOP;
}

color GetArrowColor(int markerType, double result)
{
    switch(markerType)
    {
        case WD_ARROW_BUY:
            return clrBlue;
        case WD_ARROW_SELL:
            return clrRed;
        case WD_ARROW_TP:
            return clrGreen;
        case WD_ARROW_SL:
            return result > 0.0 ? clrGreen : clrRed;
        default:
            return result >= 0.0 ? clrGreen : clrRed;
    }
}

string GetArrowTooltip(int markerType, double lots, double result)
{
    if(markerType == WD_ARROW_BUY || markerType == WD_ARROW_SELL)
        return "";

    string tooltip = "Lots: " + DoubleToString(lots, 2);
    tooltip += "\nProfit: " + DoubleToString(result, 2);
    return tooltip;
}

void DrawArrow(string name, datetime arrowTime, double arrowPrice, int markerType, int orderType, double result)
{
    if(arrowTime <= 0 || arrowPrice <= 0.0)
        return;

    int secondsPerBar = (int)(Period() * 60);
    if(secondsPerBar <= 0)
        secondsPerBar = 60;

    int halfWidthSeconds = secondsPerBar / 2;
    if(halfWidthSeconds < 60)
        halfWidthSeconds = 60;

    double visiblePriceMin = WindowPriceMin();
    double visiblePriceMax = WindowPriceMax();
    double visiblePriceRange = visiblePriceMax - visiblePriceMin;
    if(visiblePriceRange <= 0.0)
        visiblePriceRange = High[0] - Low[0];
    if(visiblePriceRange <= 0.0)
        visiblePriceRange = Point * 200.0;

    long chartHeightPixels = ChartGetInteger(0, CHART_HEIGHT_IN_PIXELS, 0);
    if(chartHeightPixels <= 0)
        chartHeightPixels = 400;

    double pricePerPixel = visiblePriceRange / chartHeightPixels;
    double height = MathMax(pricePerPixel * 18.0, Point * 40.0);

    bool isOpenMarker = (markerType == WD_ARROW_BUY || markerType == WD_ARROW_SELL);
    datetime anchorTime = isOpenMarker ? arrowTime - secondsPerBar : arrowTime + secondsPerBar;
    datetime tipTime = isOpenMarker ? anchorTime + halfWidthSeconds : anchorTime - halfWidthSeconds;
    datetime baseTime = isOpenMarker ? anchorTime - halfWidthSeconds : anchorTime + halfWidthSeconds;

    double tipPrice = arrowPrice;
    double upperBasePrice = arrowPrice + (height * 0.5);
    double lowerBasePrice = arrowPrice - (height * 0.5);
    color markerColor = GetArrowColor(markerType, result);

    if(ObjectFind(0, name) < 0)
    {
        if(!ObjectCreate(0, name, OBJ_TRIANGLE, 0, tipTime, tipPrice, baseTime, upperBasePrice, baseTime, lowerBasePrice))
        {
            Print("WARNING: failed to create triangle ", name, " err=", GetLastError());
            return;
        }

        ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
        ObjectSetInteger(0, name, OBJPROP_HIDDEN, false);
        ObjectSetInteger(0, name, OBJPROP_WIDTH, 3);
    }
    else
    {
        if(!ObjectMove(0, name, 0, tipTime, tipPrice))
            Print("WARNING: failed to move triangle point 0 ", name, " err=", GetLastError());
        if(!ObjectMove(0, name, 1, baseTime, upperBasePrice))
            Print("WARNING: failed to move triangle point 1 ", name, " err=", GetLastError());
        if(!ObjectMove(0, name, 2, baseTime, lowerBasePrice))
            Print("WARNING: failed to move triangle point 2 ", name, " err=", GetLastError());
    }

    ObjectSetInteger(0, name, OBJPROP_COLOR, markerColor);
    ObjectSetInteger(0, name, OBJPROP_STYLE, STYLE_SOLID);
    ObjectSetInteger(0, name, OBJPROP_BACK, true);
    ObjectSetInteger(0, name, OBJPROP_FILL, true);
    ObjectSetString(0, name, OBJPROP_TOOLTIP, GetArrowTooltip(markerType, OrderLots(), result));
}

int GetCloseArrowType()
{
    double tolerance = MathMax(Point * 2.0, 0.0000001);
    double closePrice = OrderClosePrice();
    double tp = OrderTakeProfit();
    double sl = OrderStopLoss();

    if(tp > 0.0 && MathAbs(closePrice - tp) <= tolerance)
        return WD_ARROW_TP;

    if(sl > 0.0 && MathAbs(closePrice - sl) <= tolerance)
        return WD_ARROW_SL;

    return WD_ARROW_CLOSE;
}

void DrawOpenOrderArrows()
{
    int total = OrdersTotal();
    for(int i = 0; i < total; i++)
    {
        if(!OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
            continue;
        if(OrderSymbol() != Symbol())
            continue;

        int orderType = OrderType();
        if(orderType != OP_BUY && orderType != OP_SELL)
            continue;

        string name = WD_CUSTOM_ARROW_PREFIX + "OPEN_" + IntegerToString(OrderTicket());
        int markerType = orderType == OP_BUY ? WD_ARROW_BUY : WD_ARROW_SELL;
        DrawArrow(name, OrderOpenTime(), OrderOpenPrice(), markerType, orderType, 0.0);
    }
}

void DrawClosedOrderArrows()
{
    int total = OrdersHistoryTotal();
    for(int i = 0; i < total; i++)
    {
        if(!OrderSelect(i, SELECT_BY_POS, MODE_HISTORY))
            continue;
        if(OrderSymbol() != Symbol())
            continue;

        int orderType = OrderType();
        if(orderType != OP_BUY && orderType != OP_SELL)
            continue;

        string openName = WD_CUSTOM_ARROW_PREFIX + "OPEN_" + IntegerToString(OrderTicket());
        int openMarkerType = orderType == OP_BUY ? WD_ARROW_BUY : WD_ARROW_SELL;
        DrawArrow(openName, OrderOpenTime(), OrderOpenPrice(), openMarkerType, orderType, 0.0);

        double result = OrderProfit() + OrderSwap() + OrderCommission();
        string name = WD_CUSTOM_ARROW_PREFIX + "CLOSE_" + IntegerToString(OrderTicket());
        DrawArrow(name, OrderCloseTime(), OrderClosePrice(), GetCloseArrowType(), orderType, result);
    }
}

void UpdateVisibleObjects()
{
    if(!custom_arrows)
    {
        DeleteCustomArrows();
        return;
    }

    int total = ObjectsTotal(0, 0, -1);
    for(int i = total - 1; i >= 0; i--)
    {
        string name = ObjectName(0, i);
        if(name == "")
            continue;

        if(StringFind(name, WD_CUSTOM_ARROW_PREFIX) == 0 && StringFind(name, "_LABEL") != -1)
        {
            ObjectDelete(0, name);
            continue;
        }

        if(StringFind(name, WD_CUSTOM_ARROW_PREFIX) == 0)
            continue;

        int objectType = ObjectType(name);
        if(IsArrowObjectType(objectType))
            ObjectDelete(0, name);
    }

    DrawOpenOrderArrows();
    DrawClosedOrderArrows();
    ChartRedraw(0);
}

#endif