
#property copyright "Copyright 2025"
#property link      ""
#property strict


string version = "3.9";

//----------------------------------------------------------------------- INPUTS

input bool show_lines = true;
input bool no_orders = false;
input bool custom_arrows = true;

//-----------------------------------------------------------------------

string WD_LINE_PREFIX = "L_";
string WD_STATS_LABEL = "WD_STATS";
string WD_CUSTOM_ARROW_PREFIX = "WD_ARROW_";
string g_tester_filename = "";
string g_result = "";
string g_decision = "";

// stats
int g_numDscAbove = 0;
int g_numAscBelow = 0;
int g_ordersArr[];
int g_cnt = 0;
int g_buyCnt = 0;
int g_sellCnt = 0;
double g_lots = 0.0;
double g_profit = 0.0;

#include "wd_tester_hash.mqh"
#include "wd_main.mqh"
#include "wd_tester_ui.mqh"

//-----------------------------------------------------------------------

string ReadAllText(string filepath)
{
    g_tester_filename = filepath;

    int fileHandle = FileOpen(filepath, FILE_READ|FILE_TXT);
    if(fileHandle == INVALID_HANDLE)
    {
        int err = GetLastError();
        Print("WARNING: Failed to open file: ", filepath, " Result: ", err);
        return "EMPTY";
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

bool IntArrayRemoveAt(int &arr[], int index)
{
    int n = ArraySize(arr);
    if(index < 0 || index >= n)
        return false;

    for(int i = index; i < n - 1; i++)
        arr[i] = arr[i + 1];

    ArrayResize(arr, n - 1);
    return true;
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

    if(IsTesting() && IsVisualMode())
        return;

    DeleteCustomArrows();
}

void OnOrderClosed(int ticket)
{
    // called form UpdateOrdersArrayPre
    // NOTE: order is already selected here 

    // get order profit
    double profit = OrderProfit();
    string type = OrderType() == OP_BUY ? "BUY" : "SELL";

    string statsStr = "Order closed: " + IntegerToString(ticket) + " type: " + type + " profit: " + DoubleToString(profit, Digits);
    statsStr += " | numDscAbove: " + IntegerToString(g_numDscAbove) + " numAscBelow: " + IntegerToString(g_numAscBelow) + " | ";
    statsStr += "cnt: " + IntegerToString(g_cnt) + " buyCnt: " + IntegerToString(g_buyCnt) + " sellCnt: " + IntegerToString(g_sellCnt) + " all lots: " + DoubleToString(g_lots, 2) + " all profit: " + DoubleToString(g_profit, Digits);

    Print(statsStr);
    Log(statsStr);
}

void UpdateOrdersArrayPre()
{
    // check g_ordersArr for any orders that are now closed and remove them from the array
    for(int i = ArraySize(g_ordersArr) - 1; i >= 0; i--)
    {
        int ticket = g_ordersArr[i];
        if(!OrderSelect(ticket, SELECT_BY_TICKET))
        {
            Log("error");
        }

        // check order close time
        datetime closeTime = OrderCloseTime();
        if(closeTime > 0)
        {
            // order is closed
            IntArrayRemoveAt(g_ordersArr, i);

            OnOrderClosed(ticket);
        }
    }
}

void UpdateOrdersArrayPost()
{
    // add all open orders to g_ordersArr

    ArrayResize(g_ordersArr, 0);
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

        int ticket = OrderTicket();
        ArrayResize(g_ordersArr, ArraySize(g_ordersArr) + 1);
        g_ordersArr[ArraySize(g_ordersArr) - 1] = ticket;
    }
}

void OnTickMustBeTheSameForProduction()
{
    //
    // Shoudl be the same for production!
    CheckBE();
    CheckTrailingTP();
    CheckSetupTP();
    CheckCloseIfNoProfitAfterNCandles();
    // Shoudl be the same for production!
    //
}

void OnTick()
{
    RefreshRates();

    UpdateTesterStatsOverlay();

    datetime currentTime = Time[0];
    datetime decisionTime = currentTime - (15 * 60);  // 15 minutes before
    
    // If decision is from previous day - skip
    string currentDate = TimeToString(currentTime, TIME_DATE);
    string decisionDate = TimeToString(decisionTime, TIME_DATE);
    if(currentDate != decisionDate)
    {
        static datetime lastSkippedTime = 0;
        if(lastSkippedTime != currentTime)
            lastSkippedTime = currentTime;
        
        DeleteWdLines();
        PrintErrorIfBothBuyAndSellOpen();

        //
        // Shoudl be the same for production!
        OnTickMustBeTheSameForProduction();
        // Shoudl be the same for production!
        //

        return;
    }
    
    string timeStr = TimeToString(decisionTime, TIME_DATE|TIME_MINUTES);
    StringReplace(timeStr, "2025", "25");
    StringReplace(timeStr, "2026", "26");
    StringReplace(timeStr, ".", "-");
    StringReplace(timeStr, ":", "-");
    StringReplace(timeStr, " ", "-");

    string result_filename = "wd_tester/" + timeStr + "_decision.txt";
    g_decision = ReadAllText(result_filename);

    int firstQuote = StringFind(g_decision, "\"");
    int secondQuote = StringFind(g_decision, "\"", firstQuote + 1);
    g_result = StringSubstr(g_decision, firstQuote + 1, secondQuote - firstQuote - 1);
    g_decision = StringSubstr(g_decision, secondQuote + 2, StringLen(g_decision) - secondQuote - 2);

    bool isNoCrossedDecision = (StringFind(g_decision, "log: no crossed", 0) == 0);
    bool isNoneResult = (StringFind(g_result, "NONE", 0) == 0);
    bool skipNoCrossedLog = (isNoCrossedDecision && isNoneResult);
    if(!skipNoCrossedLog)
        Print("Decision: " + g_decision + " Result: " + g_result);
    
    DeleteWdLines();
    DrawLinesFromResult();
    PrintErrorIfBothBuyAndSellOpen();

//-----------------------------------------------------------------------

    UpdateOrdersArrayPre();

    if(!no_orders)
    {
        // Format is like "BUY ABOVE 21917.27"
        int ticket = ExecuteWdDecision(g_decision, 0.01);
        if (ticket > 0)
            Log("new order ticket: " + IntegerToString(ticket) + " for time: " + TimeToString(TimeCurrent()));
        //else
            //Log("no order for time: " + TimeToString(TimeCurrent()));
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

    //
    // Shoudl be the same for production!
    OnTickMustBeTheSameForProduction();
    // Shoudl be the same for production!
    //

    UpdateOrdersArrayPost();
    UpdateVisibleObjects();
}
