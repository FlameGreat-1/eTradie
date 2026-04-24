//+------------------------------------------------------------------+
//| ZeroMQ_EA.mq5 - eTradie ZeroMQ Bridge Expert Advisor             |
//|                                                                  |
//| Production-Ready Enterprise-Grade MT5 Bridge                     |
//|                                                                  |
//| Serves as the REP socket endpoint for the Python ZmqClient.      |
//| Receives JSON commands, executes MT5 API calls, returns JSON.    |
//|                                                                  |
//| Dependencies (MUST be installed manually):                       |
//|   1. mql-zmq: https://github.com/dingmaotu/mql-zmq              |
//|      - Copy Zmq folder to MQL5/Include/                          |
//|      - Includes libzmq.dll for Windows                           |
//|   2. JAson: https://github.com/sierkov/JAson                    |
//|      - Copy JAson.mqh to MQL5/Include/                           |
//|                                                                  |
//| Installation:                                                    |
//|   1. Install dependencies above                                  |
//|   2. Copy this file to MQL5/Experts/ in your MT5 data folder     |
//|   3. Attach to any chart (symbol doesn't matter)                 |
//|   4. Enable "Allow DLL imports" in EA settings                   |
//|   5. Configure parameters below (port, auth token, magic, etc.)  |
//|                                                                  |
//| Security:                                                        |
//|   - Authentication token required (set AUTH_TOKEN parameter)     |
//|   - No credentials sent over ZMQ                                 |
//|   - You log into broker account manually in MT5 terminal         |
//|   - Token must match Python client's MT5_ZMQ_AUTH_TOKEN          |
//|                                                                  |
//| Version History:                                                 |
//|   1.00 - Initial release                                         |
//|   2.00 - Production hardening: auth, validation, logging         |
//+------------------------------------------------------------------+
#property copyright "eTradie"
#property version   "2.00"

#include <Zmq/Zmq.mqh>
#include <JAson.mqh>

//+------------------------------------------------------------------+
//| Input Parameters                                                 |
//+------------------------------------------------------------------+
input group "=== Network Configuration ==="
input int    ZMQ_PORT        = 5555;     // ZeroMQ REP port
input int    RECV_TIMEOUT_MS = 1000;     // ZMQ receive timeout (ms)
input int    SEND_TIMEOUT_MS = 5000;     // ZMQ send timeout (ms)

input group "=== Security ==="
input string AUTH_TOKEN      = "etradie_secure_token_2026";  // Authentication token (must match Python client)

input group "=== Trading Configuration ==="
input long   MAGIC_NUMBER    = 20260321; // Magic number for eTradie orders
input int    MAX_SLIPPAGE    = 10;       // Maximum slippage in points
input double MAX_LOT_SIZE    = 10.0;     // Maximum lot size per order
input double MAX_TOTAL_EXPOSURE = 50.0;  // Maximum total exposure (lots)
input double MAX_DRAWDOWN_PCT = 20.0;    // Maximum drawdown % before blocking trades

input group "=== Performance ==="
input int    TIMER_MS        = 50;       // Timer interval (ms) - 50ms = 20 polls/sec

input group "=== Logging ==="
input bool   ENABLE_DEBUG_LOG = false;   // Enable debug logging
input bool   LOG_COMMANDS     = true;    // Log all commands received

//+------------------------------------------------------------------+
//| Global Variables                                                 |
//+------------------------------------------------------------------+
Context g_context;
Socket  g_socket(g_context, ZMQ_REP);
bool    g_initialized = false;
bool    g_authenticated = false;
datetime g_start_time = 0;
long    g_command_count = 0;
string  g_last_error = "";

//+------------------------------------------------------------------+
//| Logging Levels                                                   |
//+------------------------------------------------------------------+
enum LOG_LEVEL
{
   LOG_DEBUG,
   LOG_INFO,
   LOG_WARN,
   LOG_ERROR
};

//+------------------------------------------------------------------+
//| Expert Initialization                                            |
//+------------------------------------------------------------------+
int OnInit()
{
   g_start_time = TimeCurrent();
   string endpoint = "tcp://*:" + IntegerToString(ZMQ_PORT);

   // Configure socket timeouts
   g_socket.setReceiveTimeout(RECV_TIMEOUT_MS);
   g_socket.setSendTimeout(SEND_TIMEOUT_MS);
   g_socket.setLinger(0);

   // Bind to endpoint
   if(!g_socket.bind(endpoint))
   {
      Log(LOG_ERROR, "FATAL: Failed to bind to " + endpoint);
      Alert("ZMQ_EA: Failed to bind to port " + IntegerToString(ZMQ_PORT));
      return INIT_FAILED;
   }

   g_initialized = true;
   EventSetMillisecondTimer(TIMER_MS);
   
   Log(LOG_INFO, "=== eTradie ZeroMQ Bridge Started ===");
   Log(LOG_INFO, "Endpoint: " + endpoint);
   Log(LOG_INFO, "Magic Number: " + IntegerToString(MAGIC_NUMBER));
   Log(LOG_INFO, "Max Slippage: " + IntegerToString(MAX_SLIPPAGE) + " points");
   Log(LOG_INFO, "Timer Interval: " + IntegerToString(TIMER_MS) + "ms");
   Log(LOG_INFO, "Authentication: " + (AUTH_TOKEN != "" ? "ENABLED" : "DISABLED"));
   Log(LOG_INFO, "Ready for commands");
   
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
      // NOTE: REP socket must NOT send without a prior recv (ZMQ EFSM protocol).
      // Python client detects disconnection via its own socket timeout.
      g_socket.unbind("tcp://*:" + IntegerToString(ZMQ_PORT));
      // g_socket.close() removed — socket closes automatically via ~Socket() destructor
      g_initialized = false;
      
      Log(LOG_INFO, "=== eTradie ZeroMQ Bridge Stopped ===");
      Log(LOG_INFO, "Reason: " + GetDeinitReason(reason));
      Log(LOG_INFO, "Total commands processed: " + IntegerToString(g_command_count));
      Log(LOG_INFO, "Uptime: " + IntegerToString((long)(TimeCurrent() - g_start_time)) + " seconds");
   }
}

//+------------------------------------------------------------------+
//| Timer Event - Poll for Incoming ZMQ Messages                     |
//+------------------------------------------------------------------+
void OnTimer()
{
   if(!g_initialized) return;

   ZmqMsg request;
   if(!g_socket.recv(request, true))  // Non-blocking
      return;

   string raw = request.getData();
   if(StringLen(raw) == 0) return;

   // Parse JSON command
   CJAVal cmd;
   if(!cmd.Deserialize(raw))
   {
      SendError("Invalid JSON format");
      Log(LOG_ERROR, "Invalid JSON received: " + raw);
      return;
   }

   string command = cmd["command"].ToStr();
   
   // Log command if enabled
   if(LOG_COMMANDS)
      Log(LOG_INFO, "Command received: " + command);
   
   g_command_count++;
   
   // Route command to handler
   string response = "";
   
   if(command == "PING")                         response = HandlePing(cmd);
   else if(command == "HEALTH")                  response = HandleHealth();
   else if(!g_authenticated)                     response = "{\"error\":\"Not authenticated. Send PING with valid auth_token first.\"}";
   else if(command == "CANDLES")                 response = HandleCandles(cmd);
   else if(command == "CANDLE_LATEST")           response = HandleCandleLatest(cmd);
   else if(command == "SYMBOL_INFO")             response = HandleSymbolInfo(cmd);
   else if(command == "ACCOUNT_INFO")            response = HandleAccountInfo();
   else if(command == "POSITIONS")               response = HandlePositions();
   else if(command == "PENDING_ORDERS")          response = HandlePendingOrders();
   else if(command == "POSITION")                response = HandlePosition(cmd);
   else if(command == "TICK_PRICE")              response = HandleTickPrice(cmd);
   else if(command == "ORDER_SEND")              response = HandleOrderSend(cmd);
   else if(command == "ORDER_CANCEL")            response = HandleOrderCancel(cmd);
   else if(command == "POSITION_MODIFY")         response = HandlePositionModify(cmd);
   else if(command == "POSITION_CLOSE_PARTIAL")  response = HandlePositionClosePartial(cmd);
   else if(command == "POSITION_CLOSE")          response = HandlePositionClose(cmd);
   else if(command == "GET_ALL_SYMBOLS")          response = HandleGetAllSymbols();
   else                                          response = "{\"error\":\"Unknown command: " + command + "\"}";

   // Send response
   ZmqMsg reply(response);
   g_socket.send(reply);
}

//+------------------------------------------------------------------+
//| Send Error Response                                              |
//+------------------------------------------------------------------+
void SendError(string msg)
{
   g_last_error = msg;
   ZmqMsg reply("{\"error\":\"" + msg + "\"}");
   g_socket.send(reply);
}

//+------------------------------------------------------------------+
//| Logging Function                                                 |
//+------------------------------------------------------------------+
void Log(LOG_LEVEL level, string message)
{
   // Skip debug logs if not enabled
   if(level == LOG_DEBUG && !ENABLE_DEBUG_LOG)
      return;
   
   string prefix;
   switch(level)
   {
      case LOG_DEBUG: prefix = "[DEBUG]"; break;
      case LOG_INFO:  prefix = "[INFO]";  break;
      case LOG_WARN:  prefix = "[WARN]";  break;
      case LOG_ERROR: prefix = "[ERROR]"; break;
   }
   
   Print(prefix, " [ZMQ_EA] ", TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS), " - ", message);
}

//+------------------------------------------------------------------+
//| Get Deinitialization Reason String                               |
//+------------------------------------------------------------------+
string GetDeinitReason(int reason)
{
   switch(reason)
   {
      case REASON_PROGRAM:      return "EA removed from chart";
      case REASON_REMOVE:       return "EA removed from chart";
      case REASON_RECOMPILE:    return "EA recompiled";
      case REASON_CHARTCHANGE:  return "Chart symbol/period changed";
      case REASON_CHARTCLOSE:   return "Chart closed";
      case REASON_PARAMETERS:   return "Input parameters changed";
      case REASON_ACCOUNT:      return "Account changed";
      case REASON_TEMPLATE:     return "Template changed";
      case REASON_INITFAILED:   return "Initialization failed";
      case REASON_CLOSE:        return "Terminal closing";
      default:                  return "Unknown reason (" + IntegerToString(reason) + ")";
   }
}

//+------------------------------------------------------------------+
//| PING - Authentication & Health Check                             |
//+------------------------------------------------------------------+
string HandlePing(CJAVal &cmd)
{
   // Validate authentication token
   string token = cmd["auth_token"].ToStr();
   
   if(AUTH_TOKEN != "" && token != AUTH_TOKEN)
   {
      Log(LOG_WARN, "Authentication failed - invalid token");
      return "{\"error\":\"Invalid authentication token\"}";
   }
   
   g_authenticated = true;
   Log(LOG_INFO, "Authentication successful");
   
   CJAVal j;
   j["status"] = "ok";
   j["authenticated"] = true;
   j["magic_number"] = MAGIC_NUMBER;
   j["server_time"] = (long)TimeCurrent();
   return j.Serialize();
}

//+------------------------------------------------------------------+
//| HEALTH - System Health Check                                     |
//+------------------------------------------------------------------+
string HandleHealth()
{
   CJAVal j;
   j["status"]            = "ok";
   j["uptime_seconds"]    = (long)(TimeCurrent() - g_start_time);
   j["commands_processed"] = g_command_count;
   j["last_error"]        = g_last_error;
   j["mt5_connected"]     = TerminalInfoInteger(TERMINAL_CONNECTED);
   j["trade_allowed"]     = TerminalInfoInteger(TERMINAL_TRADE_ALLOWED);
   j["authenticated"]     = g_authenticated;
   j["account_number"]    = AccountInfoInteger(ACCOUNT_LOGIN);
   j["account_server"]    = AccountInfoString(ACCOUNT_SERVER);
   return j.Serialize();
}


//+------------------------------------------------------------------+
//| ACCOUNT_INFO - Account Information                               |
//+------------------------------------------------------------------+
string HandleAccountInfo()
{
   CJAVal j;
   j["balance"]     = AccountInfoDouble(ACCOUNT_BALANCE);
   j["equity"]      = AccountInfoDouble(ACCOUNT_EQUITY);
   j["margin"]      = AccountInfoDouble(ACCOUNT_MARGIN);
   j["margin_free"] = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
   j["margin_level"] = AccountInfoDouble(ACCOUNT_MARGIN_LEVEL);
   j["profit"]      = AccountInfoDouble(ACCOUNT_PROFIT);
   j["currency"]    = AccountInfoString(ACCOUNT_CURRENCY);
   j["leverage"]    = AccountInfoInteger(ACCOUNT_LEVERAGE);
   j["trade_allowed"] = TerminalInfoInteger(TERMINAL_TRADE_ALLOWED);
   j["trade_expert"] = AccountInfoInteger(ACCOUNT_TRADE_EXPERT);
   
   Log(LOG_DEBUG, "Account info retrieved - Balance: " + DoubleToString(j["balance"].ToDbl(), 2));
   return j.Serialize();
}

//+------------------------------------------------------------------+
//| POSITIONS - All Open Positions                                   |
//+------------------------------------------------------------------+
string HandlePositions()
{
   CJAVal arr;
   int total = PositionsTotal();
   int count = 0;
   
   for(int i = 0; i < total; i++)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(!PositionSelectByTicket(ticket)) continue;

      CJAVal p;
      p["symbol"]        = PositionGetString(POSITION_SYMBOL);
      p["type"]          = (int)PositionGetInteger(POSITION_TYPE);
      p["type_str"]      = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? "BUY" : "SELL";
      p["price_open"]    = PositionGetDouble(POSITION_PRICE_OPEN);
      p["price_current"] = PositionGetDouble(POSITION_PRICE_CURRENT);
      p["sl"]            = PositionGetDouble(POSITION_SL);
      p["tp"]            = PositionGetDouble(POSITION_TP);
      p["volume"]        = PositionGetDouble(POSITION_VOLUME);
      p["profit"]        = PositionGetDouble(POSITION_PROFIT);
      p["swap"]          = PositionGetDouble(POSITION_SWAP);
      p["commission"]    = PositionGetDouble(POSITION_COMMISSION);
      p["ticket"]        = (long)ticket;
      p["magic"]         = (long)PositionGetInteger(POSITION_MAGIC);
      p["comment"]       = PositionGetString(POSITION_COMMENT);
      p["time_setup"]    = (long)PositionGetInteger(POSITION_TIME);
      p["identifier"]    = (long)PositionGetInteger(POSITION_IDENTIFIER);
      
      arr[count++] = p;
   }
   if(count == 0) return "[]";
   
   Log(LOG_DEBUG, "Retrieved " + IntegerToString(count) + " open positions");
   return arr.Serialize();
}

//+------------------------------------------------------------------+
//| PENDING_ORDERS - All Pending Orders                              |
//+------------------------------------------------------------------+
string HandlePendingOrders()
{
   CJAVal arr;
   int total = OrdersTotal();
   int count = 0;
   
   for(int i = 0; i < total; i++)
   {
      ulong ticket = OrderGetTicket(i);
      if(ticket == 0) continue;

      CJAVal o;
      o["symbol"]       = OrderGetString(ORDER_SYMBOL);
      o["type"]         = (int)OrderGetInteger(ORDER_TYPE);
      o["type_str"]     = GetOrderTypeString((int)OrderGetInteger(ORDER_TYPE));
      o["price_open"]   = OrderGetDouble(ORDER_PRICE_OPEN);
      o["sl"]           = OrderGetDouble(ORDER_SL);
      o["tp"]           = OrderGetDouble(ORDER_TP);
      o["volume"]       = OrderGetDouble(ORDER_VOLUME_CURRENT);
      o["ticket"]       = (long)ticket;
      o["magic"]        = (long)OrderGetInteger(ORDER_MAGIC);
      o["comment"]      = OrderGetString(ORDER_COMMENT);
      o["time_setup"]   = (long)OrderGetInteger(ORDER_TIME_SETUP);
      o["time_expiration"] = (long)OrderGetInteger(ORDER_TIME_EXPIRATION);
      
      arr[count++] = o;
   }
   if(count == 0) return "[]";
   
   Log(LOG_DEBUG, "Retrieved " + IntegerToString(count) + " pending orders");
   return arr.Serialize();
}

//+------------------------------------------------------------------+
//| POSITION - Single Position by Ticket                             |
//+------------------------------------------------------------------+
string HandlePosition(CJAVal &cmd)
{
   long ticket = (long)StringToInteger(cmd["ticket"].ToStr());
   
   if(ticket <= 0)
   {
      Log(LOG_ERROR, "Invalid ticket number: " + IntegerToString(ticket));
      return "{\"error\":\"Invalid ticket number\"}";
   }
   
   if(!PositionSelectByTicket((ulong)ticket))
   {
      Log(LOG_WARN, "Position not found: " + IntegerToString(ticket));
      return "{\"error\":\"Position not found: " + IntegerToString(ticket) + "\"}";
   }

   CJAVal p;
   p["symbol"]        = PositionGetString(POSITION_SYMBOL);
   p["type"]          = (int)PositionGetInteger(POSITION_TYPE);
   p["type_str"]      = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? "BUY" : "SELL";
   p["price_open"]    = PositionGetDouble(POSITION_PRICE_OPEN);
   p["price_current"] = PositionGetDouble(POSITION_PRICE_CURRENT);
   p["sl"]            = PositionGetDouble(POSITION_SL);
   p["tp"]            = PositionGetDouble(POSITION_TP);
   p["volume"]        = PositionGetDouble(POSITION_VOLUME);
   p["profit"]        = PositionGetDouble(POSITION_PROFIT);
   p["swap"]          = PositionGetDouble(POSITION_SWAP);
   p["commission"]    = PositionGetDouble(POSITION_COMMISSION);
   p["ticket"]        = ticket;
   p["magic"]         = (long)PositionGetInteger(POSITION_MAGIC);
   p["comment"]       = PositionGetString(POSITION_COMMENT);
   p["time_setup"]    = (long)PositionGetInteger(POSITION_TIME);
   
   Log(LOG_DEBUG, "Position retrieved: " + IntegerToString(ticket));
   return p.Serialize();
}

//+------------------------------------------------------------------+
//| TICK_PRICE - Live Bid/Ask Price                                  |
//+------------------------------------------------------------------+
string HandleTickPrice(CJAVal &cmd)
{
   string symbol = cmd["symbol"].ToStr();
   
   // Validate symbol
   if(!ValidateSymbol(symbol))
   {
      Log(LOG_ERROR, "Invalid or unavailable symbol: " + symbol);
      return "{\"error\":\"Symbol not available: " + symbol + "\"}";
   }
   
   MqlTick tick;
   if(!SymbolInfoTick(symbol, tick))
   {
      Log(LOG_ERROR, "Failed to get tick for symbol: " + symbol);
      return "{\"error\":\"Tick not available for " + symbol + "\"}";
   }

   CJAVal j;
   j["symbol"] = symbol;
   j["bid"]    = tick.bid;
   j["ask"]    = tick.ask;
   j["last"]   = tick.last;
   j["volume"] = (long)tick.volume;
   j["time"]   = (long)tick.time;
   j["spread"] = (int)SymbolInfoInteger(symbol, SYMBOL_SPREAD);
   
   Log(LOG_DEBUG, "Tick price: " + symbol + " Bid=" + DoubleToString(tick.bid, 5) + " Ask=" + DoubleToString(tick.ask, 5));
   return j.Serialize();
}

//+------------------------------------------------------------------+
//| SYMBOL_INFO - Symbol Specifications                              |
//+------------------------------------------------------------------+
string HandleSymbolInfo(CJAVal &cmd)
{
   string symbol = cmd["symbol"].ToStr();
   
   // Validate and select symbol
   if(!ValidateSymbol(symbol))
   {
      Log(LOG_ERROR, "Symbol not found: " + symbol);
      return "{\"error\":\"Symbol not found: " + symbol + "\"}";
   }

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
   
   Log(LOG_DEBUG, "Symbol info retrieved: " + symbol);
   return j.Serialize();
}

//+------------------------------------------------------------------+
//| CANDLES - Historical OHLCV Data                                  |
//+------------------------------------------------------------------+
string HandleCandles(CJAVal &cmd)
{
   string symbol    = cmd["symbol"].ToStr();
   string tf_str    = cmd["timeframe"].ToStr();
   int    count     = (int)StringToInteger(cmd["count"].ToStr());
   
   // Validate symbol
   if(!ValidateSymbol(symbol))
   {
      Log(LOG_ERROR, "Invalid symbol for candles: " + symbol);
      return "{\"error\":\"Symbol not available: " + symbol + "\"}";
   }
   
   // Validate and convert timeframe
   ENUM_TIMEFRAMES tf = StringToTimeframe(tf_str);
   if(tf == PERIOD_CURRENT)
   {
      Log(LOG_ERROR, "Invalid timeframe: " + tf_str);
      return "{\"error\":\"Invalid timeframe: " + tf_str + "\"}";
   }
   
   // Validate count
   if(count <= 0) count = 500;
   if(count > 10000) count = 10000;

   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   int copied = CopyRates(symbol, tf, 0, count, rates);
   
   if(copied <= 0)
   {
      int error = GetLastError();
      Log(LOG_ERROR, "Failed to get candles for " + symbol + " " + tf_str + " - Error: " + IntegerToString(error));
      return "{\"error\":\"No data for " + symbol + " " + tf_str + " (Error: " + IntegerToString(error) + ")\"}";
   }

   // Reverse to chronological order (oldest first)
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
   
   Log(LOG_DEBUG, "Retrieved " + IntegerToString(copied) + " candles for " + symbol + " " + tf_str);
   return arr.Serialize();
}

//+------------------------------------------------------------------+
//| CANDLE_LATEST - Most Recent Candle                               |
//+------------------------------------------------------------------+
string HandleCandleLatest(CJAVal &cmd)
{
   string symbol = cmd["symbol"].ToStr();
   string tf_str = cmd["timeframe"].ToStr();
   
   // Validate symbol
   if(!ValidateSymbol(symbol))
   {
      Log(LOG_ERROR, "Invalid symbol for latest candle: " + symbol);
      return "{\"error\":\"Symbol not available: " + symbol + "\"}";
   }
   
   // Validate and convert timeframe
   ENUM_TIMEFRAMES tf = StringToTimeframe(tf_str);
   if(tf == PERIOD_CURRENT)
   {
      Log(LOG_ERROR, "Invalid timeframe: " + tf_str);
      return "{\"error\":\"Invalid timeframe: " + tf_str + "\"}";
   }

   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   int copied = CopyRates(symbol, tf, 0, 1, rates);
   
   if(copied <= 0)
   {
      int error = GetLastError();
      Log(LOG_ERROR, "Failed to get latest candle for " + symbol + " " + tf_str + " - Error: " + IntegerToString(error));
      return "{\"error\":\"No data for " + symbol + " " + tf_str + " (Error: " + IntegerToString(error) + ")\"}";
   }

   CJAVal bar;
   bar["time"]        = (long)rates[0].time;
   bar["open"]        = rates[0].open;
   bar["high"]        = rates[0].high;
   bar["low"]         = rates[0].low;
   bar["close"]       = rates[0].close;
   bar["tick_volume"] = (long)rates[0].tick_volume;
   bar["real_volume"] = (long)rates[0].real_volume;
   bar["spread"]      = (int)rates[0].spread;
   
   Log(LOG_DEBUG, "Latest candle: " + symbol + " " + tf_str + " Close=" + DoubleToString(rates[0].close, 5));
   return bar.Serialize();
}

//+------------------------------------------------------------------+
//| GET_ALL_SYMBOLS - All Symbols from Market Watch                  |
//+------------------------------------------------------------------+
string HandleGetAllSymbols()
{
   int total = SymbolsTotal(false);  // false = all symbols
   int count = 0;
   
   string json = "{\"symbols\":[";
   StringReserve(json, total * 100); // Pre-allocate memory for ~100 bytes per symbol
   
   for(int i = 0; i < total; i++)
   {
      string name = SymbolName(i, false);
      if(StringLen(name) == 0) continue;

      string desc = SymbolInfoString(name, SYMBOL_DESCRIPTION);
      string path = SymbolInfoString(name, SYMBOL_PATH);
      
      // Safe JSON escaping: replace backslashes with forward slashes, and double quotes with single quotes.
      // This guarantees no infinite replacement loops and perfectly valid JSON strings.
      StringReplace(desc, "\\", "/");
      StringReplace(desc, "\"", "'");
      StringReplace(path, "\\", "/");
      StringReplace(path, "\"", "'");
      StringReplace(name, "\\", "/");
      StringReplace(name, "\"", "'");
      
      if(count > 0) StringAdd(json, ",");
      
      StringAdd(json, "{\"name\":\"");
      StringAdd(json, name);
      StringAdd(json, "\",\"description\":\"");
      StringAdd(json, desc);
      StringAdd(json, "\",\"path\":\"");
      StringAdd(json, path);
      StringAdd(json, "\"}");
      
      count++;
   }
   
   StringAdd(json, "],\"count\":");
   StringAdd(json, IntegerToString(count));
   StringAdd(json, "}");
   
   Log(LOG_DEBUG, "Retrieved " + IntegerToString(count) + " symbols directly from broker");
   return json;
}

//+------------------------------------------------------------------+
//| Validate Symbol - Check if symbol exists and is tradeable        |
//+------------------------------------------------------------------+
bool ValidateSymbol(string symbol)
{
   // Try to select symbol
   if(!SymbolSelect(symbol, true))
   {
      Log(LOG_WARN, "Symbol not found in Market Watch: " + symbol);
      return false;
   }
   
   // Check if symbol info is available
   if(SymbolInfoInteger(symbol, SYMBOL_SELECT) == 0)
   {
      Log(LOG_WARN, "Symbol not available: " + symbol);
      return false;
   }
   
   return true;
}

//+------------------------------------------------------------------+
//| Get Order Type String                                            |
//+------------------------------------------------------------------+
string GetOrderTypeString(int type)
{
   switch(type)
   {
      case ORDER_TYPE_BUY:        return "BUY";
      case ORDER_TYPE_SELL:       return "SELL";
      case ORDER_TYPE_BUY_LIMIT:  return "BUY_LIMIT";
      case ORDER_TYPE_SELL_LIMIT: return "SELL_LIMIT";
      case ORDER_TYPE_BUY_STOP:   return "BUY_STOP";
      case ORDER_TYPE_SELL_STOP:  return "SELL_STOP";
      case ORDER_TYPE_BUY_STOP_LIMIT:  return "BUY_STOP_LIMIT";
      case ORDER_TYPE_SELL_STOP_LIMIT: return "SELL_STOP_LIMIT";
      default: return "UNKNOWN";
   }
}

//+------------------------------------------------------------------+
//| ORDER_SEND - Place Market or Limit Order                         |
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

   // Validate symbol
   if(!ValidateSymbol(symbol))
   {
      Log(LOG_ERROR, "Order rejected - invalid symbol: " + symbol);
      return "{\"error\":\"Symbol not available: " + symbol + "\",\"status\":\"REJECTED\"}";
   }

   // Check if trading is allowed
   if((ENUM_SYMBOL_TRADE_MODE)SymbolInfoInteger(symbol, SYMBOL_TRADE_MODE) == SYMBOL_TRADE_MODE_DISABLED)
   {
      Log(LOG_ERROR, "Order rejected - trading disabled for: " + symbol);
      return "{\"error\":\"Trading disabled for symbol: " + symbol + "\",\"status\":\"REJECTED\"}";
   }

   // Validate and normalize lot size
   double min_lot = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
   double max_lot = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);
   double step    = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
   
   if(lots < min_lot)
   {
      Log(LOG_ERROR, "Order rejected - lot size too small: " + DoubleToString(lots, 2) + " (min: " + DoubleToString(min_lot, 2) + ")");
      return "{\"error\":\"Lot size below minimum: " + DoubleToString(min_lot, 2) + "\",\"status\":\"REJECTED\"}";
   }
   
   if(lots > max_lot || lots > MAX_LOT_SIZE)
   {
      double limit = MathMin(max_lot, MAX_LOT_SIZE);
      Log(LOG_ERROR, "Order rejected - lot size too large: " + DoubleToString(lots, 2) + " (max: " + DoubleToString(limit, 2) + ")");
      return "{\"error\":\"Lot size exceeds maximum: " + DoubleToString(limit, 2) + "\",\"status\":\"REJECTED\"}";
   }
   
   // Normalize to step - derive precision from step value
   int lot_digits = (int)MathRound(-MathLog10(step));
   if(lot_digits < 0) lot_digits = 0;
   lots = NormalizeDouble(MathFloor(lots / step) * step, lot_digits);

   // Check risk limits
   if(!CheckRiskLimits(symbol, lots))
   {
      Log(LOG_ERROR, "Order rejected - risk limits exceeded");
      return "{\"error\":\"Risk limits exceeded (max exposure or drawdown)\",\"status\":\"REJECTED\"}";
   }

   // Prepare trade request
   MqlTradeRequest request = {};
   MqlTradeResult  result  = {};

   request.symbol    = symbol;
   request.volume    = lots;
   request.sl        = NormalizePrice(symbol, sl);
   request.tp        = NormalizePrice(symbol, tp);
   request.comment   = comment;
   request.magic     = MAGIC_NUMBER;
   request.deviation = MAX_SLIPPAGE;

   if(type_str == "MARKET")
   {
      request.action = TRADE_ACTION_DEAL;
      request.type   = (direction == "BUY") ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
      
      // Get current price
      MqlTick tick;
      if(SymbolInfoTick(symbol, tick))
         request.price = (direction == "BUY") ? tick.ask : tick.bid;
      else
         request.price = price;
      
      request.price = NormalizePrice(symbol, request.price);
      request.type_filling = ORDER_FILLING_IOC;
   }
   else if(type_str == "LIMIT")
   {
      request.action = TRADE_ACTION_PENDING;
      request.type   = (direction == "BUY") ? ORDER_TYPE_BUY_LIMIT : ORDER_TYPE_SELL_LIMIT;
      request.price  = NormalizePrice(symbol, price);
      request.type_filling = ORDER_FILLING_RETURN;
   }
   else if(type_str == "STOP")
   {
      request.action = TRADE_ACTION_PENDING;
      request.type   = (direction == "BUY") ? ORDER_TYPE_BUY_STOP : ORDER_TYPE_SELL_STOP;
      request.price  = NormalizePrice(symbol, price);
      request.type_filling = ORDER_FILLING_RETURN;
   }
   else
   {
      Log(LOG_ERROR, "Order rejected - invalid order type: " + type_str);
      return "{\"error\":\"Invalid order type: " + type_str + "\",\"status\":\"REJECTED\"}";
   }

   // Validate stop levels
   if(!ValidateStopLevels(symbol, request.type, request.price, request.sl, request.tp))
   {
      Log(LOG_ERROR, "Order rejected - invalid stop levels");
      return "{\"error\":\"Stop levels too close to market price\",\"status\":\"REJECTED\"}";
   }

   // Send order
   if(!OrderSend(request, result))
   {
      string error_msg = "OrderSend failed: " + IntegerToString(result.retcode) + " - " + result.comment;
      Log(LOG_ERROR, error_msg);
      
      CJAVal j;
      j["order_id"] = 0;
      j["price"]    = 0.0;
      j["status"]   = "REJECTED";
      j["error"]    = error_msg;
      j["retcode"]  = (int)result.retcode;
      return j.Serialize();
   }

   // Success
   CJAVal j;
   j["order_id"] = (long)result.order;
   j["deal_id"]  = (long)result.deal;
   j["price"]    = result.price;
   j["volume"]   = result.volume;
   j["status"]   = (type_str == "MARKET") ? "FILLED" : "PLACED";
   j["error"]    = "";

   Log(LOG_INFO, "Order placed: " + symbol + " " + direction + " " + type_str + 
       " lots=" + DoubleToString(lots, 2) + " order=" + IntegerToString(result.order) + 
       " price=" + DoubleToString(result.price, 5));
   
   return j.Serialize();
}

//+------------------------------------------------------------------+
//| ORDER_CANCEL - Cancel Pending Order                              |
//+------------------------------------------------------------------+
string HandleOrderCancel(CJAVal &cmd)
{
   long order_id = (long)StringToInteger(cmd["order_id"].ToStr());

   if(order_id <= 0)
   {
      Log(LOG_ERROR, "Invalid order ID for cancel: " + IntegerToString(order_id));
      return "{\"success\":false,\"error\":\"Invalid order ID\"}";
   }

   // Verify order exists
   if(!OrderSelect(order_id))
   {
      Log(LOG_WARN, "Order not found for cancel: " + IntegerToString(order_id));
      return "{\"success\":false,\"error\":\"Order not found: " + IntegerToString(order_id) + "\"}";
   }

   MqlTradeRequest request = {};
   MqlTradeResult  result  = {};

   request.action = TRADE_ACTION_REMOVE;
   request.order  = (ulong)order_id;

   if(!OrderSend(request, result))
   {
      string error_msg = "Cancel failed: " + IntegerToString(result.retcode) + " - " + result.comment;
      Log(LOG_ERROR, error_msg);
      
      CJAVal j;
      j["success"] = false;
      j["error"]   = error_msg;
      j["retcode"] = (int)result.retcode;
      return j.Serialize();
   }

   CJAVal j;
   j["success"] = true;
   j["error"]   = "";
   
   Log(LOG_INFO, "Order cancelled: " + IntegerToString(order_id));
   return j.Serialize();
}

//+------------------------------------------------------------------+
//| POSITION_MODIFY - Adjust SL/TP                                   |
//+------------------------------------------------------------------+
string HandlePositionModify(CJAVal &cmd)
{
   long   ticket = (long)StringToInteger(cmd["ticket"].ToStr());
   double sl     = cmd["stop_loss"].ToDbl();
   double tp     = cmd["take_profit"].ToDbl();

   if(ticket <= 0)
   {
      Log(LOG_ERROR, "Invalid ticket for modify: " + IntegerToString(ticket));
      return "{\"success\":false,\"error\":\"Invalid ticket number\"}";
   }

   if(!PositionSelectByTicket((ulong)ticket))
   {
      Log(LOG_WARN, "Position not found for modify: " + IntegerToString(ticket));
      return "{\"success\":false,\"error\":\"Position not found: " + IntegerToString(ticket) + "\"}";
   }

   string symbol = PositionGetString(POSITION_SYMBOL);
   long   type   = PositionGetInteger(POSITION_TYPE);
   double price  = PositionGetDouble(POSITION_PRICE_CURRENT);

   // Normalize prices
   sl = NormalizePrice(symbol, sl);
   tp = NormalizePrice(symbol, tp);

   // Validate stop levels
   ENUM_ORDER_TYPE order_type = (type == POSITION_TYPE_BUY) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   if(!ValidateStopLevels(symbol, order_type, price, sl, tp))
   {
      Log(LOG_ERROR, "Modify rejected - invalid stop levels for ticket: " + IntegerToString(ticket));
      return "{\"success\":false,\"error\":\"Stop levels too close to market price\"}";
   }

   MqlTradeRequest request = {};
   MqlTradeResult  result  = {};

   request.action   = TRADE_ACTION_SLTP;
   request.position = (ulong)ticket;
   request.symbol   = symbol;
   request.sl       = sl;
   request.tp       = tp;

   if(!OrderSend(request, result))
   {
      string error_msg = "Modify failed: " + IntegerToString(result.retcode) + " - " + result.comment;
      Log(LOG_ERROR, error_msg);
      
      CJAVal j;
      j["success"] = false;
      j["error"]   = error_msg;
      j["retcode"] = (int)result.retcode;
      return j.Serialize();
   }

   CJAVal j;
   j["success"] = true;
   j["error"]   = "";
   
   Log(LOG_INFO, "Position modified: ticket=" + IntegerToString(ticket) + 
       " SL=" + DoubleToString(sl, 5) + " TP=" + DoubleToString(tp, 5));
   
   return j.Serialize();
}

//+------------------------------------------------------------------+
//| POSITION_CLOSE_PARTIAL - Partial Position Close                  |
//+------------------------------------------------------------------+
string HandlePositionClosePartial(CJAVal &cmd)
{
   long   ticket = (long)StringToInteger(cmd["ticket"].ToStr());
   double volume = cmd["volume"].ToDbl();

   if(ticket <= 0)
   {
      Log(LOG_ERROR, "Invalid ticket for partial close: " + IntegerToString(ticket));
      return "{\"success\":false,\"close_price\":0.0,\"error\":\"Invalid ticket number\"}";
   }

   if(!PositionSelectByTicket((ulong)ticket))
   {
      Log(LOG_WARN, "Position not found for partial close: " + IntegerToString(ticket));
      return "{\"success\":false,\"close_price\":0.0,\"error\":\"Position not found: " + IntegerToString(ticket) + "\"}";
   }

   string symbol        = PositionGetString(POSITION_SYMBOL);
   long   type          = PositionGetInteger(POSITION_TYPE);
   double total_volume  = PositionGetDouble(POSITION_VOLUME);
   double step          = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);

   // Validate volume
   if(volume <= 0 || volume >= total_volume)
   {
      Log(LOG_ERROR, "Invalid partial close volume: " + DoubleToString(volume, 2) + " (position: " + DoubleToString(total_volume, 2) + ")");
      return "{\"success\":false,\"close_price\":0.0,\"error\":\"Invalid volume for partial close\"}";
   }

   // Normalize volume
   volume = NormalizeDouble(MathFloor(volume / step) * step, 2);

   MqlTradeRequest request = {};
   MqlTradeResult  result  = {};

   request.action       = TRADE_ACTION_DEAL;
   request.position     = (ulong)ticket;
   request.symbol       = symbol;
   request.volume       = volume;
   request.type         = (type == POSITION_TYPE_BUY) ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
   request.deviation    = MAX_SLIPPAGE;
   request.type_filling = ORDER_FILLING_IOC;
   request.magic        = MAGIC_NUMBER;

   // Get current price
   MqlTick tick;
   if(SymbolInfoTick(symbol, tick))
      request.price = (type == POSITION_TYPE_BUY) ? tick.bid : tick.ask;
   else
   {
      Log(LOG_ERROR, "Failed to get tick for partial close");
      return "{\"success\":false,\"close_price\":0.0,\"error\":\"Failed to get current price\"}";
   }

   request.price = NormalizePrice(symbol, request.price);

   if(!OrderSend(request, result))
   {
      string error_msg = "Partial close failed: " + IntegerToString(result.retcode) + " - " + result.comment;
      Log(LOG_ERROR, error_msg);
      
      CJAVal j;
      j["success"]     = false;
      j["close_price"] = 0.0;
      j["error"]       = error_msg;
      j["retcode"]     = (int)result.retcode;
      return j.Serialize();
   }

   CJAVal j;
   j["success"]     = true;
   j["close_price"] = result.price;
   j["volume"]      = result.volume;
   j["deal_id"]     = (long)result.deal;
   j["error"]       = "";
   
   Log(LOG_INFO, "Partial close: ticket=" + IntegerToString(ticket) + 
       " volume=" + DoubleToString(volume, 2) + " price=" + DoubleToString(result.price, 5));
   
   return j.Serialize();
}

//+------------------------------------------------------------------+
//| POSITION_CLOSE - Full Position Close                             |
//+------------------------------------------------------------------+
string HandlePositionClose(CJAVal &cmd)
{
   long ticket = (long)StringToInteger(cmd["ticket"].ToStr());

   if(ticket <= 0)
   {
      Log(LOG_ERROR, "Invalid ticket for close: " + IntegerToString(ticket));
      return "{\"success\":false,\"close_price\":0.0,\"error\":\"Invalid ticket number\"}";
   }

   if(!PositionSelectByTicket((ulong)ticket))
   {
      Log(LOG_WARN, "Position not found for close: " + IntegerToString(ticket));
      return "{\"success\":false,\"close_price\":0.0,\"error\":\"Position not found: " + IntegerToString(ticket) + "\"}";
   }

   string symbol = PositionGetString(POSITION_SYMBOL);
   double volume = PositionGetDouble(POSITION_VOLUME);
   long   type   = PositionGetInteger(POSITION_TYPE);

   MqlTradeRequest request = {};
   MqlTradeResult  result  = {};

   request.action       = TRADE_ACTION_DEAL;
   request.position     = (ulong)ticket;
   request.symbol       = symbol;
   request.volume       = volume;
   request.type         = (type == POSITION_TYPE_BUY) ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
   request.deviation    = MAX_SLIPPAGE;
   request.type_filling = ORDER_FILLING_IOC;
   request.magic        = MAGIC_NUMBER;

   // Get current price
   MqlTick tick;
   if(SymbolInfoTick(symbol, tick))
      request.price = (type == POSITION_TYPE_BUY) ? tick.bid : tick.ask;
   else
   {
      Log(LOG_ERROR, "Failed to get tick for close");
      return "{\"success\":false,\"close_price\":0.0,\"error\":\"Failed to get current price\"}";
   }

   request.price = NormalizePrice(symbol, request.price);

   if(!OrderSend(request, result))
   {
      string error_msg = "Close failed: " + IntegerToString(result.retcode) + " - " + result.comment;
      Log(LOG_ERROR, error_msg);
      
      CJAVal j;
      j["success"]     = false;
      j["close_price"] = 0.0;
      j["error"]       = error_msg;
      j["retcode"]     = (int)result.retcode;
      return j.Serialize();
   }

   CJAVal j;
   j["success"]     = true;
   j["close_price"] = result.price;
   j["volume"]      = result.volume;
   j["deal_id"]     = (long)result.deal;
   j["error"]       = "";
   
   Log(LOG_INFO, "Position closed: ticket=" + IntegerToString(ticket) + 
       " price=" + DoubleToString(result.price, 5));
   
   return j.Serialize();
}

//+------------------------------------------------------------------+
//| Helper Functions                                                 |
//+------------------------------------------------------------------+

//+------------------------------------------------------------------+
//| Check Risk Limits Before Opening Position                        |
//+------------------------------------------------------------------+
bool CheckRiskLimits(string symbol, double lots)
{
   // Check total exposure across all positions
   double total_exposure = 0.0;
   int total = PositionsTotal();
   
   for(int i = 0; i < total; i++)
   {
      ulong tk = PositionGetTicket(i);
      if(tk == 0) continue;
      if(!PositionSelectByTicket(tk)) continue;
      total_exposure += PositionGetDouble(POSITION_VOLUME);
   }
   
   if(total_exposure + lots > MAX_TOTAL_EXPOSURE)
   {
      Log(LOG_WARN, "Risk check failed - Total exposure would exceed limit: " + 
          DoubleToString(total_exposure + lots, 2) + " > " + DoubleToString(MAX_TOTAL_EXPOSURE, 2));
      return false;
   }
   
   // Check drawdown percentage
   double equity  = AccountInfoDouble(ACCOUNT_EQUITY);
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   
   if(balance > 0)
   {
      double drawdown_pct = ((balance - equity) / balance) * 100.0;
      
      if(drawdown_pct > MAX_DRAWDOWN_PCT)
      {
         Log(LOG_WARN, "Risk check failed - Drawdown exceeds limit: " + 
             DoubleToString(drawdown_pct, 2) + "% > " + DoubleToString(MAX_DRAWDOWN_PCT, 2) + "%");
         return false;
      }
   }
   
   // Check free margin
   double margin_required = 0.0;
   if(!OrderCalcMargin(ORDER_TYPE_BUY, symbol, lots, SymbolInfoDouble(symbol, SYMBOL_ASK), margin_required))
   {
      Log(LOG_ERROR, "Failed to calculate margin requirement");
      return false;
   }
   
   double free_margin = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
   if(margin_required > free_margin)
   {
      Log(LOG_WARN, "Risk check failed - Insufficient free margin: " + 
          DoubleToString(free_margin, 2) + " < " + DoubleToString(margin_required, 2));
      return false;
   }
   
   return true;
}

//+------------------------------------------------------------------+
//| Validate Stop Loss and Take Profit Levels                        |
//+------------------------------------------------------------------+
bool ValidateStopLevels(string symbol, ENUM_ORDER_TYPE order_type, double price, double sl, double tp)
{
   int stops_level = (int)SymbolInfoInteger(symbol, SYMBOL_TRADE_STOPS_LEVEL);
   double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
   
   // If stops_level is 0, broker doesn't enforce minimum distance
   if(stops_level == 0)
      return true;
   
   double min_distance = stops_level * point;
   
   // Validate SL
   if(sl > 0)
   {
      double sl_distance = 0;
      
      if(order_type == ORDER_TYPE_BUY || order_type == ORDER_TYPE_BUY_LIMIT || order_type == ORDER_TYPE_BUY_STOP)
         sl_distance = price - sl;
      else
         sl_distance = sl - price;
      
      if(sl_distance < min_distance)
      {
         Log(LOG_WARN, "SL too close to price: " + DoubleToString(sl_distance / point, 1) + 
             " points (min: " + IntegerToString(stops_level) + " points)");
         return false;
      }
   }
   
   // Validate TP
   if(tp > 0)
   {
      double tp_distance = 0;
      
      if(order_type == ORDER_TYPE_BUY || order_type == ORDER_TYPE_BUY_LIMIT || order_type == ORDER_TYPE_BUY_STOP)
         tp_distance = tp - price;
      else
         tp_distance = price - tp;
      
      if(tp_distance < min_distance)
      {
         Log(LOG_WARN, "TP too close to price: " + DoubleToString(tp_distance / point, 1) + 
             " points (min: " + IntegerToString(stops_level) + " points)");
         return false;
      }
   }
   
   return true;
}

//+------------------------------------------------------------------+
//| Normalize Price to Symbol's Tick Size                            |
//+------------------------------------------------------------------+
double NormalizePrice(string symbol, double price)
{
   if(price == 0) return 0;
   
   double tick_size = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE);
   int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
   
   if(tick_size > 0)
      price = NormalizeDouble(MathRound(price / tick_size) * tick_size, digits);
   else
      price = NormalizeDouble(price, digits);
   
   return price;
}

//+------------------------------------------------------------------+
//| Convert Timeframe String to ENUM_TIMEFRAMES......                |
//+------------------------------------------------------------------+
ENUM_TIMEFRAMES StringToTimeframe(string tf)
{
   if(tf == "M1" || tf == "1m")   return PERIOD_M1;
   if(tf == "M5" || tf == "5m")   return PERIOD_M5;
   if(tf == "M15" || tf == "15m") return PERIOD_M15;
   if(tf == "M30" || tf == "30m") return PERIOD_M30;
   if(tf == "H1" || tf == "1h")   return PERIOD_H1;
   if(tf == "H3" || tf == "3h")   return PERIOD_H3;
   if(tf == "H4" || tf == "4h")   return PERIOD_H4;
   if(tf == "H6" || tf == "6h")   return PERIOD_H6;
   if(tf == "H8" || tf == "8h")   return PERIOD_H8;
   if(tf == "H12" || tf == "12h") return PERIOD_H12;
   if(tf == "D1" || tf == "1d")   return PERIOD_D1;
   if(tf == "W1" || tf == "1w")   return PERIOD_W1;
   if(tf == "MN1" || tf == "1M")  return PERIOD_MN1;
   
   Log(LOG_WARN, "Unknown timeframe string: " + tf + " - using PERIOD_CURRENT");
   return PERIOD_CURRENT;
}

//+------------------------------------------------------------------+