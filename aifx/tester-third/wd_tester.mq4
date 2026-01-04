
#property copyright "Copyright 2025"
#property link      ""
#property strict

string version = "1.0";

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

    StringTrimLeft(content);
    StringTrimRight(content);
    return content;
}

void ApplyBlackOnWhiteTheme()
{
    long chartId = 0;

    ChartSetInteger(chartId, CHART_MODE, CHART_CANDLES);

    ChartSetInteger(chartId, CHART_COLOR_BACKGROUND, clrWhite);
    ChartSetInteger(chartId, CHART_COLOR_FOREGROUND, clrBlack);
    ChartSetInteger(chartId, CHART_COLOR_GRID, clrSilver);
    ChartSetInteger(chartId, CHART_COLOR_VOLUME, clrBlack);

    ChartSetInteger(chartId, CHART_COLOR_CHART_UP, clrWhite);
    ChartSetInteger(chartId, CHART_COLOR_CHART_DOWN, clrBlack);

    ChartRedraw(chartId);
}

int OnInit()
{   
   Print("version: " + version);
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
