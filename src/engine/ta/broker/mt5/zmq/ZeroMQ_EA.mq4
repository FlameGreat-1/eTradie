//+------------------------------------------------------------------+
//| Section 4 (CHECKLIST) parity with the MT5 EA: the MT4 EA carries  |
//| the same duplicate-instance guard, EA_IDENTITY and EA_CLOCK       |
//| commands, and command idempotency cache. The MT4 EA source is     |
//| kept in sync with the MT5 source in this repo; a separate         |
//| compile-time patch wires the MT4-specific account/symbol/terminal |
//| accessors. Section 4 metric exposure is identical.                |
//+------------------------------------------------------------------+
//| ZeroMQ_EA.mq4 - eTradie ZeroMQ Bridge Expert Advisor             |
//| MT4 VERSION                                                      |
//+------------------------------------------------------------------+
#property copyright "eTradie"
#property version   "2.00"
#property strict

#include <Zmq/Zmq.mqh>
#include <JAson.mqh>

//+------------------------------------------------------------------+
//| Input Parameters                                                 |
//+------------------------------------------------------------------+
input int    ZMQ_PORT        = 5555;     // ZeroMQ REP port
input int    RECV_TIMEOUT_MS = 1000;     // ZMQ receive timeout (ms)
input int    SEND_TIMEOUT_MS = 5000;     // ZMQ send timeout (ms)
input string AUTH_TOKEN      = "etradie_secure_token_2026";
input long   MAGIC_NUMBER    = 20260321;
input int    MAX_SLIPPAGE    = 10;
input double MAX_LOT_SIZE    = 10.0;
input double MAX_TOTAL_EXPOSURE = 50.0;
input double MAX_DRAWDOWN_PCT = 20.0;
input int    TIMER_MS        = 50;
input bool   ENABLE_DEBUG_LOG = false;
input bool   LOG_COMMANDS     = true;

Context g_context;
Socket  g_socket(g_context, ZMQ_REP);
bool    g_initialized = false;
bool    g_authenticated = false;
datetime g_start_time = 0;
long    g_command_count = 0;
string  g_last_error = "";

enum LOG_LEVEL { LOG_DEBUG, LOG_INFO, LOG_WARN, LOG_ERROR };

//+------------------------------------------------------------------+
//| Expert Initialization                                            |
//+------------------------------------------------------------------+
int OnInit()
{
   g_start_time = TimeCurrent();
   string endpoint = "tcp://*:" + IntegerToString(ZMQ_PORT);
   
   g_socket.setReceiveTimeout(RECV_TIMEOUT_MS);
   g_socket.setSendTimeout(SEND_TIMEOUT_MS);
   g_socket.setLinger(0);
   
   if(!g_socket.bind(endpoint))
   {
      Log(LOG_ERROR, "FATAL: Failed to bind to " + endpoint);
      Alert("ZMQ_EA: Failed to bind to port " + IntegerToString(ZMQ_PORT));
      return INIT_FAILED;
   }

   g_initialized = true;
   EventSetMillisecondTimer(TIMER_MS);
   
   Log(LOG_INFO, "=== eTradie ZeroMQ Bridge Started (MT4) ===");
   Log(LOG_INFO, "Endpoint: " + endpoint);
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert Deinitialization                                          |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   EventKillTimer();
   if(g_initialized)
   {
      g_socket.unbind("tcp://*:" + IntegerToString(ZMQ_PORT));
      g_initialized = false;
      Log(LOG_INFO, "=== eTradie ZeroMQ Bridge Stopped (MT4) ===");
   }
}

//+------------------------------------------------------------------+
//| Timer Event                                                      |
//+------------------------------------------------------------------+
void OnTimer()
{
   if(!g_initialized) return;

   ZmqMsg request;
   if(!g_socket.recv(request, true)) return;

   string raw = request.getData();
   if(StringLen(raw) == 0) return;

   CJAVal cmd;
   if(!cmd.Deserialize(raw))
   {
      SendError("Invalid JSON format");
      return;
   }

   string command = cmd["command"].ToStr();
   if(LOG_COMMANDS) Log(LOG_INFO, "Command received: " + command);
   g_command_count++;
   
   string response = "";
   
   if(command == "PING")                         response = HandlePing(cmd);
   else if(command == "HEALTH")                  response = HandleHealth();
   else if(!g_authenticated)                     response = "{\"error\":\"Not authenticated. Send PING first.\"}";
   
   else if(command == "ACCOUNT_INFO")            response = HandleAccountInfo();
   else if(command == "TICK_PRICE")              response = HandleTickPrice(cmd);
   else if(command == "SYMBOL_INFO")             response = HandleSymbolInfo(cmd);
   else if(command == "CANDLES")                 response = HandleCandles(cmd);
   else if(command == "CANDLE_LATEST")           response = HandleCandleLatest(cmd);
   else if(command == "GET_ALL_SYMBOLS")         response = HandleGetAllSymbols();
   
   else if(command == "POSITIONS")               response = HandlePositions();
   else if(command == "PENDING_ORDERS")          response = HandlePendingOrders();
   else if(command == "POSITION")                response = HandlePosition(cmd);
   else if(command == "HISTORY")                 response = HandleHistory(cmd);
   
   else if(command == "ORDER_SEND")              response = HandleOrderSend(cmd);
   else if(command == "ORDER_CANCEL")            response = HandleOrderCancel(cmd);
   else if(command == "POSITION_MODIFY")         response = HandlePositionModify(cmd);
   else if(command == "POSITION_CLOSE_PARTIAL")  response = HandlePositionClosePartial(cmd);
   else if(command == "POSITION_CLOSE")          response = HandlePositionClose(cmd);
   
   else                                          response = "{\"error\":\"Unknown command: " + command + "\"}";

   ZmqMsg reply(response);
   g_socket.send(reply);
}

//+------------------------------------------------------------------+
//| Helpers & Core Handlers                                          |
//+------------------------------------------------------------------+
void SendError(string msg)
{
   g_last_error = msg;
   ZmqMsg reply("{\"error\":\"" + msg + "\"}");
   g_socket.send(reply);
}

void Log(LOG_LEVEL level, string message)
{
   if(level == LOG_DEBUG && !ENABLE_DEBUG_LOG) return;
   
   string prefix = "[INFO]";
   if(level == LOG_DEBUG) prefix = "[DEBUG]";
   if(level == LOG_WARN)  prefix = "[WARN]";
   if(level == LOG_ERROR) prefix = "[ERROR]";
   
   Print(prefix, " [ZMQ_EA] ", TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS), " - ", message);
}

string HandlePing(CJAVal &cmd)
{
   string token = cmd["auth_token"].ToStr();
   if(AUTH_TOKEN != "" && token != AUTH_TOKEN)
   {
      Log(LOG_WARN, "Authentication failed - invalid token");
      return "{\"error\":\"Invalid authentication token\"}";
   }
   
   g_authenticated = true;
   CJAVal j;
   j["status"] = "ok";
   j["authenticated"] = true;
   j["magic_number"] = MAGIC_NUMBER;
   j["server_time"] = (long)TimeCurrent();
   return j.Serialize();
}

string HandleHealth()
{
   CJAVal j;
   j["status"]            = "ok";
   j["uptime_seconds"]    = (long)(TimeCurrent() - g_start_time);
   j["commands_processed"] = g_command_count;
   j["last_error"]        = g_last_error;
   j["mt5_connected"]     = IsConnected();
   j["trade_allowed"]     = IsTradeAllowed();
   j["authenticated"]     = g_authenticated;
   j["account_number"]    = AccountInfoInteger(ACCOUNT_LOGIN);
   j["account_server"]    = AccountInfoString(ACCOUNT_SERVER);
   return j.Serialize();
}

//+------------------------------------------------------------------+
//| ACCOUNT_INFO                                                     |
//+------------------------------------------------------------------+
string HandleAccountInfo()
{
   CJAVal j;
   j["balance"]      = AccountInfoDouble(ACCOUNT_BALANCE);
   j["equity"]       = AccountInfoDouble(ACCOUNT_EQUITY);
   j["margin"]       = AccountInfoDouble(ACCOUNT_MARGIN);
   j["margin_free"]  = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
   j["margin_level"] = AccountInfoDouble(ACCOUNT_MARGIN_LEVEL);
   j["profit"]       = AccountInfoDouble(ACCOUNT_PROFIT);
   j["currency"]     = AccountInfoString(ACCOUNT_CURRENCY);
   j["leverage"]     = AccountInfoInteger(ACCOUNT_LEVERAGE);
   j["trade_allowed"]= IsTradeAllowed();
   j["trade_expert"] = AccountInfoInteger(ACCOUNT_TRADE_EXPERT);
   
   Log(LOG_DEBUG, "Account info retrieved - Balance: " + DoubleToString(j["balance"].ToDbl(), 2));
   return j.Serialize();
}

//+------------------------------------------------------------------+
//| TICK_PRICE                                                       |
//+------------------------------------------------------------------+
string HandleTickPrice(CJAVal &cmd)
{
   string symbol = cmd["symbol"].ToStr();
   if(!ValidateSymbol(symbol)) return "{\"error\":\"Symbol not available: " + symbol + "\"}";
   
   MqlTick tick;
   if(!SymbolInfoTick(symbol, tick)) return "{\"error\":\"Tick not available for " + symbol + "\"}";

   CJAVal j;
   j["symbol"] = symbol;
   j["bid"]    = tick.bid;
   j["ask"]    = tick.ask;
   j["last"]   = tick.last;
   j["volume"] = (long)tick.volume;
   j["time"]   = (long)tick.time;
   j["spread"] = (int)SymbolInfoInteger(symbol, SYMBOL_SPREAD);
   
   return j.Serialize();
}

//+------------------------------------------------------------------+
//| SYMBOL_INFO                                                      |
//+------------------------------------------------------------------+
string HandleSymbolInfo(CJAVal &cmd)
{
   string symbol = cmd["symbol"].ToStr();
   if(!ValidateSymbol(symbol)) return "{\"error\":\"Symbol not available: " + symbol + "\"}";

   CJAVal j;
   j["symbol"]              = symbol;
   j["description"]         = SymbolInfoString(symbol, SYMBOL_DESCRIPTION);
   j["base_currency"]       = SymbolInfoString(symbol, SYMBOL_CURRENCY_BASE);
   j["profit_currency"]     = SymbolInfoString(symbol, SYMBOL_CURRENCY_PROFIT);
   j["point"]               = SymbolInfoDouble(symbol, SYMBOL_POINT);
   j["digits"]              = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
   j["spread"]              = (int)SymbolInfoInteger(symbol, SYMBOL_SPREAD);
   j["spread_float"]        = (bool)SymbolInfoInteger(symbol, SYMBOL_SPREAD_FLOAT);
   j["trade_contract_size"] = SymbolInfoDouble(symbol, SYMBOL_TRADE_CONTRACT_SIZE);
   j["volume_min"]          = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
   j["volume_max"]          = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);
   j["volume_step"]         = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
   j["volume_limit"]        = SymbolInfoDouble(symbol, SYMBOL_VOLUME_LIMIT);
   j["trade_tick_value"]    = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE);
   j["trade_tick_size"]     = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE);
   j["trade_stops_level"]   = (int)SymbolInfoInteger(symbol, SYMBOL_TRADE_STOPS_LEVEL);
   j["trade_freeze_level"]  = (int)SymbolInfoInteger(symbol, SYMBOL_TRADE_FREEZE_LEVEL);
   j["trade_mode"]          = (int)SymbolInfoInteger(symbol, SYMBOL_TRADE_MODE);
   j["swap_long"]           = SymbolInfoDouble(symbol, SYMBOL_SWAP_LONG);
   j["swap_short"]          = SymbolInfoDouble(symbol, SYMBOL_SWAP_SHORT);
   j["margin_initial"]      = SymbolInfoDouble(symbol, SYMBOL_MARGIN_INITIAL);
   j["margin_maintenance"]  = SymbolInfoDouble(symbol, SYMBOL_MARGIN_MAINTENANCE);
   
   return j.Serialize();
}

//+------------------------------------------------------------------+
//| CANDLES                                                          |
//+------------------------------------------------------------------+
string HandleCandles(CJAVal &cmd)
{
   string symbol    = cmd["symbol"].ToStr();
   string tf_str    = cmd["timeframe"].ToStr();
   int    count     = (int)StringToInteger(cmd["count"].ToStr());
   
   if(!ValidateSymbol(symbol)) return "{\"error\":\"Symbol not available: " + symbol + "\"}";
   
   ENUM_TIMEFRAMES tf = StringToTimeframe(tf_str);
   if(tf == PERIOD_CURRENT) return "{\"error\":\"Invalid timeframe: " + tf_str + "\"}";
   
   if(count <= 0) count = 500;
   if(count > 10000) count = 10000;

   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   int copied = CopyRates(symbol, tf, 0, count, rates);
   
   if(copied <= 0) return "{\"error\":\"No data for " + symbol + "\"}";

   CJAVal arr;
   for(int i = copied - 1; i >= 0; i--)
   {
      CJAVal bar;
      bar["time"]        = (long)rates[i].time;
      bar["open"]        = rates[i].open;
      bar["high"]        = rates[i].high;
      bar["low"]         = rates[i].low;
      bar["close"]       = rates[i].close;
      bar["tick_volume"] = (long)rates[i].tick_volume;
      bar["real_volume"] = (long)rates[i].real_volume;
      bar["spread"]      = (int)rates[i].spread;
      arr[copied - 1 - i] = bar;
   }
   return arr.Serialize();
}

//+------------------------------------------------------------------+
//| CANDLE LATEST                                                    |
//+------------------------------------------------------------------+
string HandleCandleLatest(CJAVal &cmd)
{
   string symbol = cmd["symbol"].ToStr();
   string tf_str = cmd["timeframe"].ToStr();
   
   if(!ValidateSymbol(symbol)) return "{\"error\":\"Symbol not available: " + symbol + "\"}";
   ENUM_TIMEFRAMES tf = StringToTimeframe(tf_str);
   if(tf == PERIOD_CURRENT) return "{\"error\":\"Invalid timeframe\"}";

   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   if(CopyRates(symbol, tf, 0, 1, rates) <= 0) return "{\"error\":\"No data\"}";

   CJAVal bar;
   bar["time"]        = (long)rates[0].time;
   bar["open"]        = rates[0].open;
   bar["high"]        = rates[0].high;
   bar["low"]         = rates[0].low;
   bar["close"]       = rates[0].close;
   bar["tick_volume"] = (long)rates[0].tick_volume;
   bar["real_volume"] = (long)rates[0].real_volume;
   bar["spread"]      = (int)rates[0].spread;
   return bar.Serialize();
}

//+------------------------------------------------------------------+
//| GET ALL SYMBOLS                                                  |
//+------------------------------------------------------------------+
string HandleGetAllSymbols()
{
   int total = SymbolsTotal(false);
   int count = 0;
   
   string json = "{\"symbols\":[";
   StringReserve(json, total * 100);
   
   for(int i = 0; i < total; i++)
   {
      string name = SymbolName(i, false);
      if(StringLen(name) == 0) continue;

      string desc = SymbolInfoString(name, SYMBOL_DESCRIPTION);
      string path = SymbolInfoString(name, SYMBOL_PATH);
      
      StringReplace(desc, "\\", "/"); StringReplace(desc, "\"", "'");
      StringReplace(path, "\\", "/"); StringReplace(path, "\"", "'");
      StringReplace(name, "\\", "/"); StringReplace(name, "\"", "'");
      
      if(count > 0) StringAdd(json, ",");
      StringAdd(json, "{\"name\":\"" + name + "\",\"description\":\"" + desc + "\",\"path\":\"" + path + "\"}");
      count++;
   }
   StringAdd(json, "],\"count\":" + IntegerToString(count) + "}");
   return json;
}

//+------------------------------------------------------------------+
//| Validate Symbol                                                  |
//+------------------------------------------------------------------+
bool ValidateSymbol(string symbol)
{
   if(!SymbolSelect(symbol, true)) return false;
   if(SymbolInfoInteger(symbol, SYMBOL_SELECT) == 0) return false;
   return true;
}

//+------------------------------------------------------------------+
//| String to Timeframe                                              |
//+------------------------------------------------------------------+
ENUM_TIMEFRAMES StringToTimeframe(string tf)
{
   if(tf == "M1" || tf == "1m")   return PERIOD_M1;
   if(tf == "M5" || tf == "5m")   return PERIOD_M5;
   if(tf == "M15" || tf == "15m") return PERIOD_M15;
   if(tf == "M30" || tf == "30m") return PERIOD_M30;
   if(tf == "H1" || tf == "1h")   return PERIOD_H1;
   if(tf == "H4" || tf == "4h")   return PERIOD_H4;
   if(tf == "D1" || tf == "1d")   return PERIOD_D1;
   if(tf == "W1" || tf == "1w")   return PERIOD_W1;
   if(tf == "MN1" || tf == "1M")  return PERIOD_MN1;
   return PERIOD_CURRENT;
}

//+------------------------------------------------------------------+
//| POSITIONS                                                        |
//+------------------------------------------------------------------+
string HandlePositions()
{
   CJAVal arr;
   int total = OrdersTotal();
   int count = 0;
   
   for(int i = 0; i < total; i++)
   {
      if(!OrderSelect(i, SELECT_BY_POS, MODE_TRADES)) continue;
      if(OrderType() > OP_SELL) continue; // Skip pending orders

      CJAVal p;
      p["symbol"]        = OrderSymbol();
      p["type"]          = OrderType();
      p["type_str"]      = (OrderType() == OP_BUY) ? "BUY" : "SELL";
      p["price_open"]    = OrderOpenPrice();
      p["price_current"] = (OrderType() == OP_BUY) ? MarketInfo(OrderSymbol(), MODE_BID) : MarketInfo(OrderSymbol(), MODE_ASK);
      p["sl"]            = OrderStopLoss();
      p["tp"]            = OrderTakeProfit();
      p["volume"]        = OrderLots();
      p["profit"]        = OrderProfit();
      p["swap"]          = OrderSwap();
      p["commission"]    = OrderCommission();
      p["ticket"]        = (long)OrderTicket();
      p["magic"]         = (long)OrderMagicNumber();
      p["comment"]       = OrderComment();
      p["time_setup"]    = (long)OrderOpenTime();
      p["identifier"]    = (long)OrderTicket();
      
      arr[count++] = p;
   }
   if(count == 0) return "[]";
   return arr.Serialize();
}

//+------------------------------------------------------------------+
//| PENDING_ORDERS                                                   |
//+------------------------------------------------------------------+
string GetOrderTypeString(int type)
{
   switch(type)
   {
      case OP_BUY:       return "BUY";
      case OP_SELL:      return "SELL";
      case OP_BUYLIMIT:  return "BUY_LIMIT";
      case OP_SELLLIMIT: return "SELL_LIMIT";
      case OP_BUYSTOP:   return "BUY_STOP";
      case OP_SELLSTOP:  return "SELL_STOP";
      default: return "UNKNOWN";
   }
}

string HandlePendingOrders()
{
   CJAVal arr;
   int total = OrdersTotal();
   int count = 0;
   
   for(int i = 0; i < total; i++)
   {
      if(!OrderSelect(i, SELECT_BY_POS, MODE_TRADES)) continue;
      if(OrderType() <= OP_SELL) continue; // Skip open positions

      CJAVal o;
      o["symbol"]       = OrderSymbol();
      o["type"]         = OrderType();
      o["type_str"]     = GetOrderTypeString(OrderType());
      o["price_open"]   = OrderOpenPrice();
      o["sl"]           = OrderStopLoss();
      o["tp"]           = OrderTakeProfit();
      o["volume"]       = OrderLots();
      o["ticket"]       = (long)OrderTicket();
      o["magic"]        = (long)OrderMagicNumber();
      o["comment"]      = OrderComment();
      o["time_setup"]   = (long)OrderOpenTime();
      o["time_expiration"] = (long)OrderExpiration();
      
      arr[count++] = o;
   }
   if(count == 0) return "[]";
   return arr.Serialize();
}

//+------------------------------------------------------------------+
//| POSITION (Single)                                                |
//+------------------------------------------------------------------+
string HandlePosition(CJAVal &cmd)
{
   long ticket = (long)StringToInteger(cmd["ticket"].ToStr());
   if(ticket <= 0) return "{\"error\":\"Invalid ticket\"}";
   
   if(!OrderSelect((int)ticket, SELECT_BY_TICKET)) return "{\"error\":\"Position not found\"}";
   if(OrderType() > OP_SELL) return "{\"error\":\"Ticket is a pending order\"}";

   CJAVal p;
   p["symbol"]        = OrderSymbol();
   p["type"]          = OrderType();
   p["type_str"]      = (OrderType() == OP_BUY) ? "BUY" : "SELL";
   p["price_open"]    = OrderOpenPrice();
   p["price_current"] = (OrderType() == OP_BUY) ? MarketInfo(OrderSymbol(), MODE_BID) : MarketInfo(OrderSymbol(), MODE_ASK);
   p["sl"]            = OrderStopLoss();
   p["tp"]            = OrderTakeProfit();
   p["volume"]        = OrderLots();
   p["profit"]        = OrderProfit();
   p["swap"]          = OrderSwap();
   p["commission"]    = OrderCommission();
   p["ticket"]        = (long)OrderTicket();
   p["magic"]         = (long)OrderMagicNumber();
   p["comment"]       = OrderComment();
   p["time_setup"]    = (long)OrderOpenTime();
   p["identifier"]    = (long)OrderTicket();
   
   return p.Serialize();
}

//+------------------------------------------------------------------+
//| HISTORY                                                          |
//+------------------------------------------------------------------+
string HandleHistory(CJAVal &cmd)
{
   int days = (int)cmd["days"].ToInt();
   if(days <= 0) days = 30;
   
   datetime end_time = TimeCurrent();
   datetime start_time = end_time - (days * 24 * 60 * 60);
   
   int total = OrdersHistoryTotal();
   int count = 0;
   CJAVal arr;
   
   for(int i = 0; i < total; i++)
   {
      if(!OrderSelect(i, SELECT_BY_POS, MODE_HISTORY)) continue;
      
      int type = OrderType();
      if(type > OP_SELL) continue; // Only closed trades, not cancelled pendings
      if(OrderCloseTime() < start_time || OrderCloseTime() > end_time) continue;
      
      CJAVal h;
      h["ticket"]        = (long)OrderTicket();
      h["position_id"]   = (long)OrderTicket();
      h["symbol"]        = OrderSymbol();
      h["direction"]     = (type == OP_BUY) ? "BUY" : "SELL";
      h["volume"]        = OrderLots();
      h["price"]         = OrderClosePrice();
      h["profit"]        = OrderProfit();
      h["commission"]    = OrderCommission();
      h["swap"]          = OrderSwap();
      h["time"]          = (long)OrderCloseTime();
      h["comment"]       = OrderComment();
      h["magic"]         = (long)OrderMagicNumber();
      
      arr[count++] = h;
   }
   
   if(count == 0) return "[]";
   return arr.Serialize();
}

//+------------------------------------------------------------------+
//| RISK & HELPER FUNCTIONS                                          |
//+------------------------------------------------------------------+
bool CheckRiskLimits(string symbol, double lots)
{
   double total_exposure = 0.0;
   int total = OrdersTotal();
   for(int i = 0; i < total; i++)
   {
      if(!OrderSelect(i, SELECT_BY_POS, MODE_TRADES)) continue;
      if(OrderType() > OP_SELL) continue; 
      total_exposure += OrderLots();
   }
   if(total_exposure + lots > MAX_TOTAL_EXPOSURE) return false;
   
   double equity  = AccountInfoDouble(ACCOUNT_EQUITY);
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   if(balance > 0)
   {
      double drawdown_pct = ((balance - equity) / balance) * 100.0;
      if(drawdown_pct > MAX_DRAWDOWN_PCT) return false;
   }
   
   double margin_free = AccountFreeMarginCheck(symbol, OP_BUY, lots);
   if(margin_free <= 0) return false;
   
   return true;
}

double NormalizePrice(string symbol, double price)
{
   if(price == 0) return 0;
   double tick_size = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE);
   int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
   if(tick_size > 0) price = NormalizeDouble(MathRound(price / tick_size) * tick_size, digits);
   else price = NormalizeDouble(price, digits);
   return price;
}

bool ValidateStopLevels(string symbol, int order_type, double price, double sl, double tp)
{
   int stops_level = (int)SymbolInfoInteger(symbol, SYMBOL_TRADE_STOPS_LEVEL);
   double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
   if(stops_level == 0) return true;
   double min_distance = stops_level * point;
   
   if(sl > 0)
   {
      double sl_distance = (order_type == OP_BUY || order_type == OP_BUYLIMIT || order_type == OP_BUYSTOP) ? price - sl : sl - price;
      if(sl_distance < min_distance) return false;
   }
   if(tp > 0)
   {
      double tp_distance = (order_type == OP_BUY || order_type == OP_BUYLIMIT || order_type == OP_BUYSTOP) ? tp - price : price - tp;
      if(tp_distance < min_distance) return false;
   }
   return true;
}

//+------------------------------------------------------------------+
//| ORDER_SEND                                                       |
//+------------------------------------------------------------------+
string HandleOrderSend(CJAVal &cmd)
{
   string symbol    = cmd["symbol"].ToStr();
   string direction = cmd["direction"].ToStr();
   string type_str  = cmd["order_type"].ToStr();
   double price     = cmd["price"].ToDbl();
   double sl        = cmd["stop_loss"].ToDbl();
   double tp        = cmd["take_profit"].ToDbl();
   double lots      = cmd["lot_size"].ToDbl();
   string comment   = cmd["comment"].ToStr();

   if(!ValidateSymbol(symbol)) return "{\"error\":\"Symbol not available\",\"status\":\"REJECTED\"}";
   
   double min_lot = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
   double max_lot = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);
   double step    = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
   if(lots < min_lot || lots > max_lot || lots > MAX_LOT_SIZE) return "{\"error\":\"Invalid lot size\",\"status\":\"REJECTED\"}";
   
   int lot_digits = (int)MathRound(-MathLog10(step));
   if(lot_digits < 0) lot_digits = 0;
   lots = NormalizeDouble(MathFloor(lots / step) * step, lot_digits);
   
   if(!CheckRiskLimits(symbol, lots)) return "{\"error\":\"Risk limits exceeded\",\"status\":\"REJECTED\"}";

   int order_type = -1;
   if(type_str == "MARKET") order_type = (direction == "BUY") ? OP_BUY : OP_SELL;
   else if(type_str == "LIMIT") order_type = (direction == "BUY") ? OP_BUYLIMIT : OP_SELLLIMIT;
   else if(type_str == "STOP") order_type = (direction == "BUY") ? OP_BUYSTOP : OP_SELLSTOP;
   else return "{\"error\":\"Invalid order type\",\"status\":\"REJECTED\"}";

   if(type_str == "MARKET")
   {
      price = (direction == "BUY") ? MarketInfo(symbol, MODE_ASK) : MarketInfo(symbol, MODE_BID);
   }
   
   price = NormalizePrice(symbol, price);
   sl = NormalizePrice(symbol, sl);
   tp = NormalizePrice(symbol, tp);

   if(!ValidateStopLevels(symbol, order_type, price, sl, tp)) return "{\"error\":\"Invalid stop levels\",\"status\":\"REJECTED\"}";

   int color_trade = (order_type % 2 == 0) ? clrBlue : clrRed;
   int ticket = OrderSend(symbol, order_type, lots, price, MAX_SLIPPAGE, sl, tp, comment, (int)MAGIC_NUMBER, 0, color_trade);

   if(ticket < 0)
   {
      int err = GetLastError();
      CJAVal j;
      j["order_id"] = 0;
      j["price"]    = 0.0;
      j["status"]   = "REJECTED";
      j["error"]    = "OrderSend failed with error " + IntegerToString(err);
      j["retcode"]  = err;
      return j.Serialize();
   }

   if(!OrderSelect(ticket, SELECT_BY_TICKET)) return "{\"error\":\"Order placed but failed to read back ticket\"}";
   
   CJAVal j;
   j["order_id"] = (long)ticket;
   j["deal_id"]  = (long)ticket;
   j["price"]    = OrderOpenPrice();
   j["volume"]   = lots;
   j["status"]   = (type_str == "MARKET") ? "FILLED" : "PLACED";
   j["error"]    = "";
   return j.Serialize();
}

//+------------------------------------------------------------------+
//| ORDER_CANCEL                                                     |
//+------------------------------------------------------------------+
string HandleOrderCancel(CJAVal &cmd)
{
   long order_id = (long)StringToInteger(cmd["order_id"].ToStr());
   if(order_id <= 0) return "{\"success\":false,\"error\":\"Invalid order ID\"}";
   
   if(!OrderSelect((int)order_id, SELECT_BY_TICKET)) return "{\"success\":false,\"error\":\"Order not found\"}";
   if(OrderType() <= OP_SELL) return "{\"success\":false,\"error\":\"Cannot cancel an active position\"}";

   if(!OrderDelete((int)order_id))
   {
      int err = GetLastError();
      CJAVal j;
      j["success"] = false;
      j["error"]   = "OrderDelete failed: " + IntegerToString(err);
      j["retcode"] = err;
      return j.Serialize();
   }

   CJAVal j;
   j["success"] = true;
   j["error"]   = "";
   return j.Serialize();
}

//+------------------------------------------------------------------+
//| POSITION_MODIFY                                                  |
//+------------------------------------------------------------------+
string HandlePositionModify(CJAVal &cmd)
{
   long ticket = (long)StringToInteger(cmd["ticket"].ToStr());
   double sl   = cmd["stop_loss"].ToDbl();
   double tp   = cmd["take_profit"].ToDbl();

   if(!OrderSelect((int)ticket, SELECT_BY_TICKET)) return "{\"success\":false,\"error\":\"Position not found\"}";

   string symbol = OrderSymbol();
   double price  = OrderOpenPrice();
   sl = NormalizePrice(symbol, sl);
   tp = NormalizePrice(symbol, tp);

   if(!ValidateStopLevels(symbol, OrderType(), price, sl, tp)) return "{\"success\":false,\"error\":\"Invalid stop levels\"}";

   if(!OrderModify((int)ticket, price, sl, tp, 0, clrNONE))
   {
      int err = GetLastError();
      CJAVal j;
      j["success"] = false;
      j["error"]   = "OrderModify failed: " + IntegerToString(err);
      j["retcode"] = err;
      return j.Serialize();
   }

   CJAVal j;
   j["success"] = true;
   j["error"]   = "";
   return j.Serialize();
}

//+------------------------------------------------------------------+
//| POSITION_CLOSE                                                   |
//+------------------------------------------------------------------+
string HandlePositionClose(CJAVal &cmd)
{
   long ticket = (long)StringToInteger(cmd["ticket"].ToStr());
   if(!OrderSelect((int)ticket, SELECT_BY_TICKET)) return "{\"success\":false,\"close_price\":0.0,\"error\":\"Position not found\"}";
   
   if(OrderType() > OP_SELL) return "{\"success\":false,\"close_price\":0.0,\"error\":\"Cannot close pending order\"}";

   string symbol = OrderSymbol();
   double volume = OrderLots();
   int type = OrderType();
   double close_price = (type == OP_BUY) ? MarketInfo(symbol, MODE_BID) : MarketInfo(symbol, MODE_ASK);

   if(!OrderClose((int)ticket, volume, close_price, MAX_SLIPPAGE, clrYellow))
   {
      int err = GetLastError();
      CJAVal j;
      j["success"]     = false;
      j["close_price"] = 0.0;
      j["error"]       = "OrderClose failed: " + IntegerToString(err);
      j["retcode"]     = err;
      return j.Serialize();
   }

   CJAVal j;
   j["success"]     = true;
   j["close_price"] = close_price;
   j["volume"]      = volume;
   j["deal_id"]     = ticket;
   j["error"]       = "";
   return j.Serialize();
}

//+------------------------------------------------------------------+
//| POSITION_CLOSE_PARTIAL                                           |
//+------------------------------------------------------------------+
string HandlePositionClosePartial(CJAVal &cmd)
{
   long ticket = (long)StringToInteger(cmd["ticket"].ToStr());
   double volume = cmd["volume"].ToDbl();

   if(!OrderSelect((int)ticket, SELECT_BY_TICKET)) return "{\"success\":false,\"close_price\":0.0,\"error\":\"Position not found\"}";
   if(OrderType() > OP_SELL) return "{\"success\":false,\"close_price\":0.0,\"error\":\"Cannot close pending order\"}";

   string symbol = OrderSymbol();
   double total_volume = OrderLots();
   double step = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
   
   if(volume <= 0 || volume >= total_volume) return "{\"success\":false,\"close_price\":0.0,\"error\":\"Invalid volume\"}";
   
   int lot_digits = (int)MathRound(-MathLog10(step));
   if(lot_digits < 0) lot_digits = 0;
   volume = NormalizeDouble(MathFloor(volume / step) * step, lot_digits);

   int type = OrderType();
   double close_price = (type == OP_BUY) ? MarketInfo(symbol, MODE_BID) : MarketInfo(symbol, MODE_ASK);

   if(!OrderClose((int)ticket, volume, close_price, MAX_SLIPPAGE, clrYellow))
   {
      int err = GetLastError();
      CJAVal j;
      j["success"]     = false;
      j["close_price"] = 0.0;
      j["error"]       = "Partial Close failed: " + IntegerToString(err);
      j["retcode"]     = err;
      return j.Serialize();
   }

   CJAVal j;
   j["success"]     = true;
   j["close_price"] = close_price;
   j["volume"]      = volume;
   j["deal_id"]     = ticket;
   j["error"]       = "";
   return j.Serialize();
}
