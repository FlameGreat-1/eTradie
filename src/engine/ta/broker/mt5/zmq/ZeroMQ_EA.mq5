//+------------------------------------------------------------------+
//| ZeroMQ_EA.mq5 - eTradie ZeroMQ Bridge Expert Advisor             |
//|                                                                  |
//| Serves as the REP socket endpoint for the Python ZmqClient.      |
//| Receives JSON commands, executes MT5 API calls, returns JSON.    |
//|                                                                  |
//| Installation:                                                    |
//|   1. Copy this file to MQL5/Experts/ in your MT5 data folder     |
//|   2. Attach to any chart (symbol doesn't matter)                 |
//|   3. Enable "Allow DLL imports" in EA settings                   |
//|   4. Configure ZMQ_PORT if needed (default 5555)                 |
//|                                                                  |
//| Security: No credentials are sent over ZMQ. You log into your    |
//| broker account manually in the MT5 terminal. The Engine only     |
//| sends a PING command to verify the bridge is active.             |
//+------------------------------------------------------------------+
#property copyright "eTradie"
#property version   "1.00"
#property strict

#include <Zmq/Zmq.mqh>
#include <JAson.mqh>

//--- Input parameters
input int    ZMQ_PORT        = 5555;     // ZeroMQ REP port
input int    TIMER_MS        = 1;        // Timer interval (ms) for polling
input int    RECV_TIMEOUT_MS = 1000;     // ZMQ receive timeout (ms)
input int    SEND_TIMEOUT_MS = 5000;     // ZMQ send timeout (ms)

//--- Global ZMQ objects
Context g_context;
Socket  g_socket(g_context, ZMQ_REP);
bool    g_initialized = false;

//+------------------------------------------------------------------+
//| Expert initialization                                            |
//+------------------------------------------------------------------+
int OnInit()
{
   string endpoint = "tcp://*:" + IntegerToString(ZMQ_PORT);

   g_socket.setReceiveTimeout(RECV_TIMEOUT_MS);
   g_socket.setSendTimeout(SEND_TIMEOUT_MS);
   g_socket.setLinger(0);

   if(!g_socket.bind(endpoint))
   {
      Print("[ZMQ_EA] FATAL: Failed to bind to ", endpoint);
      return INIT_FAILED;
   }

   g_initialized = true;
   EventSetMillisecondTimer(TIMER_MS);
   Print("[ZMQ_EA] Bound to ", endpoint, " - ready for commands");
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization                                          |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   EventKillTimer();
   if(g_initialized)
   {
      g_socket.unbind("tcp://*:" + IntegerToString(ZMQ_PORT));
      g_socket.close();
      g_initialized = false;
      Print("[ZMQ_EA] Socket closed");
   }
}

//+------------------------------------------------------------------+
//| Timer event - poll for incoming ZMQ messages                     |
//+------------------------------------------------------------------+
void OnTimer()
{
   if(!g_initialized) return;

   ZmqMsg request;
   if(!g_socket.recv(request, true))  // Non-blocking
      return;

   string raw = request.getData();
   if(raw == "" || raw == NULL) return;

   CJAVal cmd;
   if(!cmd.Deserialize(raw))
   {
      SendError("Invalid JSON");
      return;
   }

   string command = cmd["command"].ToStr();
   string response = "";

   if(command == "PING")                    response = HandlePing();
   else if(command == "CANDLES")             response = HandleCandles(cmd);
   else if(command == "CANDLE_LATEST")       response = HandleCandleLatest(cmd);
   else if(command == "SYMBOL_INFO")         response = HandleSymbolInfo(cmd);
   else if(command == "ACCOUNT_INFO")        response = HandleAccountInfo();
   else if(command == "POSITIONS")           response = HandlePositions();
   else if(command == "PENDING_ORDERS")      response = HandlePendingOrders();
   else if(command == "POSITION")            response = HandlePosition(cmd);
   else if(command == "TICK_PRICE")          response = HandleTickPrice(cmd);
   else if(command == "ORDER_SEND")          response = HandleOrderSend(cmd);
   else if(command == "ORDER_CANCEL")        response = HandleOrderCancel(cmd);
   else if(command == "POSITION_MODIFY")     response = HandlePositionModify(cmd);
   else if(command == "POSITION_CLOSE_PARTIAL") response = HandlePositionClosePartial(cmd);
   else if(command == "POSITION_CLOSE")      response = HandlePositionClose(cmd);
   else                                      response = "{\"error\":\"Unknown command: " + command + "\"}";

   ZmqMsg reply(response);
   g_socket.send(reply);
}

//+------------------------------------------------------------------+
//| Send error response                                              |
//+------------------------------------------------------------------+
void SendError(string msg)
{
   ZmqMsg reply("{\"error\":\"" + msg + "\"}");
   g_socket.send(reply);
}

//+------------------------------------------------------------------+
//| PING                                                             |
//+------------------------------------------------------------------+
string HandlePing()
{
   return "{\"status\":\"ok\"}";
}

//+------------------------------------------------------------------+
//| ACCOUNT_INFO                                                     |
//+------------------------------------------------------------------+
string HandleAccountInfo()
{
   CJAVal j;
   j["balance"]     = AccountInfoDouble(ACCOUNT_BALANCE);
   j["equity"]      = AccountInfoDouble(ACCOUNT_EQUITY);
   j["margin"]      = AccountInfoDouble(ACCOUNT_MARGIN);
   j["margin_free"] = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
   j["currency"]    = AccountInfoString(ACCOUNT_CURRENCY);
   return j.Serialize();
}

//+------------------------------------------------------------------+
//| POSITIONS - all open positions                                   |
//+------------------------------------------------------------------+
string HandlePositions()
{
   CJAVal arr;
   int total = PositionsTotal();
   for(int i = 0; i < total; i++)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(!PositionSelectByTicket(ticket)) continue;

      CJAVal p;
      p["symbol"]        = PositionGetString(POSITION_SYMBOL);
      p["type"]          = (int)PositionGetInteger(POSITION_TYPE);
      p["price_open"]    = PositionGetDouble(POSITION_PRICE_OPEN);
      p["price_current"] = PositionGetDouble(POSITION_PRICE_CURRENT);
      p["sl"]            = PositionGetDouble(POSITION_SL);
      p["tp"]            = PositionGetDouble(POSITION_TP);
      p["volume"]        = PositionGetDouble(POSITION_VOLUME);
      p["profit"]        = PositionGetDouble(POSITION_PROFIT);
      p["ticket"]        = (long)ticket;
      p["comment"]       = PositionGetString(POSITION_COMMENT);
      p["time_setup"]    = (long)PositionGetInteger(POSITION_TIME);
      arr[i] = p;
   }
   return arr.Serialize();
}

//+------------------------------------------------------------------+
//| PENDING_ORDERS - all pending orders                              |
//+------------------------------------------------------------------+
string HandlePendingOrders()
{
   CJAVal arr;
   int total = OrdersTotal();
   int idx = 0;
   for(int i = 0; i < total; i++)
   {
      ulong ticket = OrderGetTicket(i);
      if(ticket == 0) continue;

      CJAVal o;
      o["symbol"]     = OrderGetString(ORDER_SYMBOL);
      o["type"]       = (int)OrderGetInteger(ORDER_TYPE);
      o["price_open"] = OrderGetDouble(ORDER_PRICE_OPEN);
      o["sl"]         = OrderGetDouble(ORDER_SL);
      o["tp"]         = OrderGetDouble(ORDER_TP);
      o["volume"]     = OrderGetDouble(ORDER_VOLUME_CURRENT);
      o["ticket"]     = (long)ticket;
      o["comment"]    = OrderGetString(ORDER_COMMENT);
      o["time_setup"] = (long)OrderGetInteger(ORDER_TIME_SETUP);
      arr[idx++] = o;
   }
   return arr.Serialize();
}

//+------------------------------------------------------------------+
//| POSITION - single position by ticket                             |
//+------------------------------------------------------------------+
string HandlePosition(CJAVal &cmd)
{
   long ticket = (long)StringToInteger(cmd["ticket"].ToStr());
   if(!PositionSelectByTicket((ulong)ticket))
      return "{\"error\":\"Position not found: " + IntegerToString(ticket) + "\"}";

   CJAVal p;
   p["symbol"]        = PositionGetString(POSITION_SYMBOL);
   p["type"]          = (int)PositionGetInteger(POSITION_TYPE);
   p["price_open"]    = PositionGetDouble(POSITION_PRICE_OPEN);
   p["price_current"] = PositionGetDouble(POSITION_PRICE_CURRENT);
   p["sl"]            = PositionGetDouble(POSITION_SL);
   p["tp"]            = PositionGetDouble(POSITION_TP);
   p["volume"]        = PositionGetDouble(POSITION_VOLUME);
   p["profit"]        = PositionGetDouble(POSITION_PROFIT);
   p["ticket"]        = ticket;
   p["comment"]       = PositionGetString(POSITION_COMMENT);
   p["time_setup"]    = (long)PositionGetInteger(POSITION_TIME);
   return p.Serialize();
}

//+------------------------------------------------------------------+
//| TICK_PRICE - live bid/ask                                        |
//+------------------------------------------------------------------+
string HandleTickPrice(CJAVal &cmd)
{
   string symbol = cmd["symbol"].ToStr();
   MqlTick tick;
   if(!SymbolInfoTick(symbol, tick))
      return "{\"error\":\"Tick not available for " + symbol + "\"}";

   CJAVal j;
   j["bid"]  = tick.bid;
   j["ask"]  = tick.ask;
   j["time"] = (long)tick.time;
   return j.Serialize();
}

//+------------------------------------------------------------------+
//| SYMBOL_INFO                                                      |
//+------------------------------------------------------------------+
string HandleSymbolInfo(CJAVal &cmd)
{
   string symbol = cmd["symbol"].ToStr();
   if(!SymbolSelect(symbol, true))
      return "{\"error\":\"Symbol not found: " + symbol + "\"}";

   CJAVal j;
   j["symbol"]              = symbol;
   j["description"]         = SymbolInfoString(symbol, SYMBOL_DESCRIPTION);
   j["point"]               = SymbolInfoDouble(symbol, SYMBOL_POINT);
   j["digits"]              = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
   j["spread"]              = (int)SymbolInfoInteger(symbol, SYMBOL_SPREAD);
   j["trade_contract_size"] = SymbolInfoDouble(symbol, SYMBOL_TRADE_CONTRACT_SIZE);
   j["volume_min"]          = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
   j["volume_max"]          = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);
   j["volume_step"]         = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
   j["trade_tick_value"]    = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE);
   j["trade_tick_size"]     = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE);
   return j.Serialize();
}

//+------------------------------------------------------------------+
//| CANDLES - historical OHLCV                                       |
//+------------------------------------------------------------------+
string HandleCandles(CJAVal &cmd)
{
   string symbol    = cmd["symbol"].ToStr();
   string tf_str    = cmd["timeframe"].ToStr();
   int    count     = (int)StringToInteger(cmd["count"].ToStr());
   ENUM_TIMEFRAMES tf = StringToTimeframe(tf_str);

   if(count <= 0) count = 500;
   if(count > 10000) count = 10000;

   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   int copied = CopyRates(symbol, tf, 0, count, rates);
   if(copied <= 0)
      return "{\"error\":\"No data for " + symbol + " " + tf_str + "\"}";

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
      arr[copied - 1 - i] = bar;
   }
   return arr.Serialize();
}

//+------------------------------------------------------------------+
//| CANDLE_LATEST - most recent candle                               |
//+------------------------------------------------------------------+
string HandleCandleLatest(CJAVal &cmd)
{
   string symbol = cmd["symbol"].ToStr();
   string tf_str = cmd["timeframe"].ToStr();
   ENUM_TIMEFRAMES tf = StringToTimeframe(tf_str);

   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   int copied = CopyRates(symbol, tf, 0, 1, rates);
   if(copied <= 0)
      return "{\"error\":\"No data for " + symbol + " " + tf_str + "\"}";

   CJAVal bar;
   bar["time"]        = (long)rates[0].time;
   bar["open"]        = rates[0].open;
   bar["high"]        = rates[0].high;
   bar["low"]         = rates[0].low;
   bar["close"]       = rates[0].close;
   bar["tick_volume"] = (long)rates[0].tick_volume;
   return bar.Serialize();
}

//+------------------------------------------------------------------+
//| ORDER_SEND - place limit or market order                         |
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

   MqlTradeRequest request = {};
   MqlTradeResult  result  = {};

   request.symbol   = symbol;
   request.volume   = lots;
   request.sl       = sl;
   request.tp       = tp;
   request.comment  = comment;
   request.magic    = 20260321;  // eTradie magic number
   request.deviation = 10;       // Max slippage in points

   if(type_str == "MARKET")
   {
      request.action = TRADE_ACTION_DEAL;
      request.type   = (direction == "BUY") ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
      // For market orders, get current price
      MqlTick tick;
      if(SymbolInfoTick(symbol, tick))
         request.price = (direction == "BUY") ? tick.ask : tick.bid;
      else
         request.price = price;
      request.type_filling = ORDER_FILLING_IOC;
   }
   else // LIMIT
   {
      request.action = TRADE_ACTION_PENDING;
      request.type   = (direction == "BUY") ? ORDER_TYPE_BUY_LIMIT : ORDER_TYPE_SELL_LIMIT;
      request.price  = price;
      request.type_filling = ORDER_FILLING_RETURN;
   }

   if(!OrderSend(request, result))
   {
      CJAVal j;
      j["order_id"] = 0;
      j["price"]    = 0.0;
      j["status"]   = "REJECTED";
      j["error"]    = "OrderSend failed: " + IntegerToString(result.retcode) +
                      " - " + result.comment;
      return j.Serialize();
   }

   CJAVal j;
   j["order_id"] = (long)result.order;
   j["price"]    = result.price;
   j["status"]   = (type_str == "MARKET") ? "FILLED" : "PLACED";
   j["error"]    = "";

   Print("[ZMQ_EA] Order placed: ", symbol, " ", direction, " ", type_str,
         " lots=", lots, " order=", result.order);
   return j.Serialize();
}

//+------------------------------------------------------------------+
//| ORDER_CANCEL - cancel pending order                              |
//+------------------------------------------------------------------+
string HandleOrderCancel(CJAVal &cmd)
{
   long order_id = (long)StringToInteger(cmd["order_id"].ToStr());

   MqlTradeRequest request = {};
   MqlTradeResult  result  = {};

   request.action = TRADE_ACTION_REMOVE;
   request.order  = (ulong)order_id;

   if(!OrderSend(request, result))
   {
      CJAVal j;
      j["success"] = false;
      j["error"]   = "Cancel failed: " + IntegerToString(result.retcode) +
                     " - " + result.comment;
      return j.Serialize();
   }

   CJAVal j;
   j["success"] = true;
   j["error"]   = "";
   Print("[ZMQ_EA] Order cancelled: ", order_id);
   return j.Serialize();
}

//+------------------------------------------------------------------+
//| POSITION_MODIFY - adjust SL/TP                                   |
//+------------------------------------------------------------------+
string HandlePositionModify(CJAVal &cmd)
{
   long   ticket = (long)StringToInteger(cmd["ticket"].ToStr());
   double sl     = cmd["stop_loss"].ToDbl();
   double tp     = cmd["take_profit"].ToDbl();

   MqlTradeRequest request = {};
   MqlTradeResult  result  = {};

   request.action   = TRADE_ACTION_SLTP;
   request.position = (ulong)ticket;
   request.sl       = sl;
   request.tp       = tp;

   if(!OrderSend(request, result))
   {
      CJAVal j;
      j["success"] = false;
      j["error"]   = "Modify failed: " + IntegerToString(result.retcode) +
                     " - " + result.comment;
      return j.Serialize();
   }

   CJAVal j;
   j["success"] = true;
   j["error"]   = "";
   Print("[ZMQ_EA] Position modified: ticket=", ticket, " SL=", sl, " TP=", tp);
   return j.Serialize();
}

//+------------------------------------------------------------------+
//| POSITION_CLOSE_PARTIAL - partial close                           |
//+------------------------------------------------------------------+
string HandlePositionClosePartial(CJAVal &cmd)
{
   long   ticket = (long)StringToInteger(cmd["ticket"].ToStr());
   double volume = cmd["volume"].ToDbl();

   if(!PositionSelectByTicket((ulong)ticket))
   {
      CJAVal j;
      j["success"]     = false;
      j["close_price"] = 0.0;
      j["error"]       = "Position not found: " + IntegerToString(ticket);
      return j.Serialize();
   }

   string symbol = PositionGetString(POSITION_SYMBOL);
   long   type   = PositionGetInteger(POSITION_TYPE);

   MqlTradeRequest request = {};
   MqlTradeResult  result  = {};

   request.action    = TRADE_ACTION_DEAL;
   request.position  = (ulong)ticket;
   request.symbol    = symbol;
   request.volume    = volume;
   request.type      = (type == POSITION_TYPE_BUY) ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
   request.deviation = 10;
   request.type_filling = ORDER_FILLING_IOC;

   MqlTick tick;
   if(SymbolInfoTick(symbol, tick))
      request.price = (type == POSITION_TYPE_BUY) ? tick.bid : tick.ask;

   if(!OrderSend(request, result))
   {
      CJAVal j;
      j["success"]     = false;
      j["close_price"] = 0.0;
      j["error"]       = "Partial close failed: " + IntegerToString(result.retcode) +
                         " - " + result.comment;
      return j.Serialize();
   }

   CJAVal j;
   j["success"]     = true;
   j["close_price"] = result.price;
   j["error"]       = "";
   Print("[ZMQ_EA] Partial close: ticket=", ticket, " volume=", volume,
         " price=", result.price);
   return j.Serialize();
}

//+------------------------------------------------------------------+
//| POSITION_CLOSE - full close                                      |
//+------------------------------------------------------------------+
string HandlePositionClose(CJAVal &cmd)
{
   long ticket = (long)StringToInteger(cmd["ticket"].ToStr());

   if(!PositionSelectByTicket((ulong)ticket))
   {
      CJAVal j;
      j["success"]     = false;
      j["close_price"] = 0.0;
      j["error"]       = "Position not found: " + IntegerToString(ticket);
      return j.Serialize();
   }

   string symbol = PositionGetString(POSITION_SYMBOL);
   double volume = PositionGetDouble(POSITION_VOLUME);
   long   type   = PositionGetInteger(POSITION_TYPE);

   MqlTradeRequest request = {};
   MqlTradeResult  result  = {};

   request.action    = TRADE_ACTION_DEAL;
   request.position  = (ulong)ticket;
   request.symbol    = symbol;
   request.volume    = volume;
   request.type      = (type == POSITION_TYPE_BUY) ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
   request.deviation = 10;
   request.type_filling = ORDER_FILLING_IOC;

   MqlTick tick;
   if(SymbolInfoTick(symbol, tick))
      request.price = (type == POSITION_TYPE_BUY) ? tick.bid : tick.ask;

   if(!OrderSend(request, result))
   {
      CJAVal j;
      j["success"]     = false;
      j["close_price"] = 0.0;
      j["error"]       = "Close failed: " + IntegerToString(result.retcode) +
                         " - " + result.comment;
      return j.Serialize();
   }

   CJAVal j;
   j["success"]     = true;
   j["close_price"] = result.price;
   j["error"]       = "";
   Print("[ZMQ_EA] Position closed: ticket=", ticket, " price=", result.price);
   return j.Serialize();
}

//+------------------------------------------------------------------+
//| Convert timeframe string to ENUM_TIMEFRAMES                      |
//+------------------------------------------------------------------+
ENUM_TIMEFRAMES StringToTimeframe(string tf)
{
   if(tf == "M1")  return PERIOD_M1;
   if(tf == "M5")  return PERIOD_M5;
   if(tf == "M15") return PERIOD_M15;
   if(tf == "M30") return PERIOD_M30;
   if(tf == "H1")  return PERIOD_H1;
   if(tf == "H4")  return PERIOD_H4;
   if(tf == "D1")  return PERIOD_D1;
   if(tf == "W1")  return PERIOD_W1;
   if(tf == "MN1") return PERIOD_MN1;
   return PERIOD_H1;  // Default fallback
}
//+------------------------------------------------------------------+
