
#property copyright "Copyright 2025"
#property link      ""
#property strict

#include "wd_tester_hash.mqh"
#include "wd_main.mqh"

string version = "1.2";

//----------------------------------------------------------------------- INPUTS

input bool show_lines = true;
input bool no_orders = false;

//-----------------------------------------------------------------------

string WD_LINE_PREFIX = "WD_LINE_";
string WD_STATS_LABEL = "WD_STATS";

string ReadAllText(string filepath)
{
    int fileHandle = FileOpen(filepath, FILE_READ|FILE_TXT);
    if(fileHandle == INVALID_HANDLE)
    {
        int err = GetLastError();
        Print("ERROR: Failed to open file: ", filepath, " Error: ", err);
        return "";
    }

    string content = "";
    while(!FileIsEnding(fileHandle))
    {
        content += FileReadString(fileHandle) + " ";
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

    ChartSetInteger(chartId, CHART_SCALE, 2);
    
    ChartRedraw(chartId);
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

        positionsCount++;
        totalLots += OrderLots();
        totalProfit += (OrderProfit() + OrderSwap() + OrderCommission());
    }
}

void UpsertTesterStatsLabel(string text)
{
    // MT4 label objects don't reliably render multi-line strings.
    // Split on '\n' and create one OBJ_LABEL per line: WD_STATS_0, WD_STATS_1, ...
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

    // Delete any leftover WD_STATS_N labels from a previously longer text.
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

void PrintErrorIfBothBuyAndSellOpen()
{
    bool hasBuy = false;
    bool hasSell = false;

    int total = OrdersTotal();
    for(int i = 0; i < total; i++)
    {
        if(!OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
            continue;
        if(OrderSymbol() != Symbol())
            continue;

        int type = OrderType();
        if(type == OP_BUY)
            hasBuy = true;
        else if(type == OP_SELL)
            hasSell = true;

        if(hasBuy && hasSell)
            break;
    }

    static bool wasConflict = false;
    bool isConflict = (hasBuy && hasSell);

    if(isConflict && !wasConflict)
    {
        // TODO uncomment
        // Print("ERROR: Both BUY and SELL orders are open at the same time for ", Symbol());
        Print("WARNING: Both BUY and SELL orders are open at the same time for ", Symbol());
    }

    wasConflict = isConflict;
}

int OnInit()
{   
    Print("version: " + version);
    Print("git hash: " + WD_GIT_HASH);
    Print("show_lines: ", show_lines);

    ApplyBlackOnWhiteTheme();

    // Create stats overlay early so it is visible immediately in visual tester.
    UpdateTesterStatsOverlay();

    string wd_main_version = GetVersion();
    Print(wd_main_version);

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

    datetime currentTime = Time[0];
    string timeStr = TimeToString(currentTime, TIME_DATE|TIME_MINUTES);
    StringReplace(timeStr, "2025", "25");
    StringReplace(timeStr, "2026", "26");
    StringReplace(timeStr, ".", "-");
    StringReplace(timeStr, ":", "-");
    StringReplace(timeStr, " ", "-");

    string decision_filename = "wd_tester/" + timeStr + "_decision.txt";
    string decision = ReadAllText(decision_filename);

    string result_filename = "wd_tester/" + timeStr + "_result.txt";
    string result = ReadAllText(result_filename);

    Print("Decision: " + decision + " Result: " + result);

    DeleteWdLines();
    if (show_lines == true)
    {
        DrawLinesFromResult(result);
    }

    PrintErrorIfBothBuyAndSellOpen();

//-----------------------------------------------------------------------
    if(!no_orders)
    {
        int ticket = ExecuteWdDecision(decision);
        if (ticket > 0)
            Print("new order ticket: ", ticket);
    }
    else
    {
        static bool noOrdersLogged = false;
        if(!noOrdersLogged)
        {
            Print("no_orders=true: skipping new order creation");
            noOrdersLogged = true;
        }
    }

    CheckBE();
    CheckSetupTP();
//-----------------------------------------------------------------------

}
