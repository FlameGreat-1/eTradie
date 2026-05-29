Place the ZeroMQ_EA compiled binaries here before building the Docker image:

- `ZeroMQ_EA.ex5` — MetaTrader 5 compiled EA binary (required)
- `ZeroMQ_EA.ex4` — MetaTrader 4 compiled EA binary (required for MT4 support)

The MQL5 and MQL4 source files live at:
  `src/engine/ta/broker/mt5/zmq/ZeroMQ_EA.mq5`
  `src/engine/ta/broker/mt5/zmq/ZeroMQ_EA.mq4`

Compile using MetaEditor (Windows) and copy the resulting `.ex5` / `.ex4`
binaries into this directory before running `make build-mt-node`.

The Dockerfile verifies the SHA256 of each binary at build time via the
`EA_EX5_SHA256` and `EA_EX4_SHA256` build-args. Pass `skip` for dev builds
that do not require supply-chain verification.

Note: `ZeroMQ_EA.ex4` is currently absent from the repository. MT4 support
is therefore non-functional until the `.ex4` binary is compiled and committed.
MT5 (`.ex5`) is fully functional.