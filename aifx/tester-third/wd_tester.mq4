
#property copyright "Copyright 2025"
#property link      ""
#property strict

string version = "1.0";

input bool show_lines = false;

string WD_LINE_PREFIX = "WD_LINE_";

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

int OnInit()
{   
    Print("version: " + version);
    Print("show_lines: ", show_lines);
    ApplyBlackOnWhiteTheme();

    return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
}

void OnTick()
{
    RefreshRates();
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

    if (show_lines == true)
    {
        DeleteWdLines();
        DrawLinesFromResult(result);
    }
    else
    {
        DeleteWdLines();
    }

    if(decision == "BUY" || decision == "SELL")
    {
        double lotSize = 0.01;
        int slippage = 300;
        int takeProfit = 20000;
        int stopLoss = 5000;
        
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
