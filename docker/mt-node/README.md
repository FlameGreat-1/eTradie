# etradie-mt-node

Headless MetaTrader 4 / 5 terminal container. Runs MT under Wine
+ Xvfb so the eTradie engine can connect to a broker over the
ZeroMQ EA bridge (tcp://<mt-node-host>:5555).

## Deployment model

mt-node is **NOT** deployed as a Kubernetes workload by the helm
charts in this repository. The engine's NetworkPolicy egress rule
targeting `app.kubernetes.io/name=etradie-mt-node` was removed in a
prior audit fix; the engine talks to whatever ZeroMQ endpoint the
operator wires via the dashboard broker-connections feature.

Typical deployment options:

1. **Per-user VPS** (most common). Each user runs an mt-node
   container on their own VPS and supplies the public IP + port to
   the eTradie dashboard. Credentials never leave the VPS.

2. **MetaAPI cloud** (no container). The dashboard
   broker-connections flow with connection_type=`metaapi` uses the
   MT5_METAAPI_TOKEN platform token to provision a managed account.
   No mt-node container is needed.

3. **Operator-hosted mt-node pool** (advanced). Deploy mt-node
   containers on a dedicated host (NOT inside the etradie-system
   Kubernetes namespace) and expose them to the engine via DNS +
   firewall. A future helm/mt-node chart could codify this; not
   shipped in this audit pass because the dashboard EA pattern
   above already covers most production usage.

## Build

```bash
make build-mt-node
```

or:

```bash
docker build -t etradie-mt-node:latest docker/mt-node/
```

## Run

Required env vars (see entrypoint.sh):

- `MT_PLATFORM` - `mt4` or `mt5`
- `MT_LOGIN`    - broker account login
- `MT_PASSWORD` - broker trading password
- `MT_SERVER`   - broker server (e.g. `Exness-MT5Trial9`)
- `ZMQ_PORT`    - ZeroMQ REP port (default 5555)

```bash
docker run -d --name etradie-mt-node \
  -e MT_PLATFORM=mt5 \
  -e MT_LOGIN=12345678 \
  -e MT_PASSWORD='changeme' \
  -e MT_SERVER='Exness-MT5Trial9' \
  -p 5555:5555 \
  ghcr.io/flamegreat-1/etradie-mt-node:latest
```

## Audit notes

- HELM_AUDIT E-H5: engine egress rule that targeted mt-node pods
  is removed; engine reaches mt-node via the dashboard-configured
  broker connection (out-of-cluster network path).
- DMT-H1: MT installer SHA256 is NOT pinned at build time because
  MQL5 publishes new installers on their own cadence. Operator can
  pin via the MT5_INSTALLER_SHA256 build-arg if reproducibility is
  required.
- DMT-H2: broker credentials live in the container's INI file at
  runtime. Acceptable for an ephemeral container with no debug
  shell access; rotate the broker password if you ever exec into
  the container.
- DMT-M2: entrypoint.sh now traps SIGTERM/SIGINT for clean
  shutdown.
