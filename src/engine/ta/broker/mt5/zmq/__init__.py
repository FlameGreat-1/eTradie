"""
ZeroMQ native broker integration.

Communicates with a ZeroMQ Expert Advisor (ZeroMQ_EA.mq5) running
on a Windows PC's MT5 terminal via REQ/REP sockets.

The Engine does NOT send credentials to the EA. Authentication
is handled manually in the MT5 terminal. The Engine only sends
a PING to confirm the bridge is active.
"""

from engine.ta.broker.mt5.zmq.client import ZmqClient

__all__ = ["ZmqClient"]
