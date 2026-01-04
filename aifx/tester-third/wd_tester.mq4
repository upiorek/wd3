
#property copyright "Copyright 2025"
#property link      ""
#property strict

string version = "1.0";

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
    string filename = "wd_tester/" + timeStr + "_decision.txt";

    string content = "";
    int fileHandle = FileOpen(filename, FILE_READ|FILE_TXT);
    if(fileHandle != INVALID_HANDLE)
    {
        while(!FileIsEnding(fileHandle))
        {
            content += FileReadString(fileHandle);
        }
        Print("File content: ", content);
        FileClose(fileHandle);
    }
    else
    {
        Print("Failed to open file: ", filename);
    }

    int hourNow = TimeHour(TimeCurrent());
    bool allowNewOrders = (hourNow >= 6 && hourNow < 22);

    if(content == "BUY" || content == "SELL")
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
        
        if(content == "BUY")
        {
            tp = NormalizeDouble(Bid + tpDistance, Digits);
            sl = NormalizeDouble(Bid - slDistance, Digits);

            ResetLastError();
            ticket = OrderSend(Symbol(), OP_BUY, lotSize, NormalizeDouble(Ask, Digits), 
                slippage, sl, tp, "WD Tester Buy", 0, 0, clrGreen);
        }
        else if(content == "SELL")
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
                content,
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
