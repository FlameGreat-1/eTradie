# syntax=docker/dockerfile:1.7
# ──────────────────────────────────────────────────────────────────
# etradie-mt-node — Headless MetaTrader 4/5 via Wine + Xvfb
#
# Runs on any x86_64 Linux. No Windows license required.
#
# Build (production):
#   docker build \
#     --build-arg MT5_INSTALLER_SHA256=<sha256-from-mql5.com> \
#     --build-arg MT4_INSTALLER_SHA256=<sha256-from-mql5.com> \
#     -t ghcr.io/flamegreat-1/etradie-mt-node:0.1.0 \
#     docker/mt-node/
#
# Build (dev, SKIP installer SHA enforcement - NOT for production):
#   docker build \
#     --build-arg MT5_INSTALLER_SHA256=skip \
#     --build-arg MT4_INSTALLER_SHA256=skip \
#     -t etradie-mt-node:dev \
#     docker/mt-node/
#
# The entrypoint reads MT_PLATFORM (mt4|mt5) to decide which terminal
# binary to launch. Other inputs come from envFrom (Kubernetes Secret
# created by the engine):
#   MT_LOGIN, MT_PASSWORD, MT_ZMQ_AUTH_TOKEN (per-tenant)
#   DEFAULT_ZMQ_AUTH_TOKEN (platform fallback)
#   MT_SERVER, MT_SYMBOL, ZMQ_PORT (chart env)
# ──────────────────────────────────────────────────────────────────
FROM ubuntu:24.04

LABEL org.opencontainers.image.title="etradie-mt-node" \
      org.opencontainers.image.description="Headless MetaTrader 4/5 (Wine+Xvfb) for the eTradie self-hosted broker bridge" \
      org.opencontainers.image.vendor="eTradie" \
      org.opencontainers.image.licenses="Proprietary" \
      org.opencontainers.image.source="https://github.com/FlameGreat-1/eTradie"

ENV DEBIAN_FRONTEND=noninteractive \
    WINEDEBUG=-all \
    WINEPREFIX=/home/mt/.wine \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# Build-arg gates. Empty -> build fails. "skip" -> dev-only, SHA check
# bypassed (used by `make build-mt-node` for local iteration).
ARG MT5_INSTALLER_SHA256=""
ARG MT4_INSTALLER_SHA256=""
ARG TINI_VERSION=v0.19.0
ARG WINEHQ_BRANCH=stable

# ── System dependencies + WineHQ apt source ───────────────────────
RUN set -eux; \
    dpkg --add-architecture i386; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        ca-certificates wget gnupg apt-transport-https \
        software-properties-common procps lsof psmisc \
        xvfb x11-utils \
        python3-minimal python3-pip python3-zmq python3-psutil python3-prometheus-client \
        tzdata; \
    install -d -m 0755 /etc/apt/keyrings; \
    wget -qO- https://dl.winehq.org/wine-builds/winehq.key | gpg --dearmor -o /etc/apt/keyrings/winehq-archive.key; \
    UBUNTU_CODENAME=$(. /etc/os-release && echo "$VERSION_CODENAME"); \
    echo "deb [signed-by=/etc/apt/keyrings/winehq-archive.key] https://dl.winehq.org/wine-builds/ubuntu/ ${UBUNTU_CODENAME} main" \
        > /etc/apt/sources.list.d/winehq.list; \
    apt-get update; \
    apt-get install -y --no-install-recommends --install-recommends \
        winehq-${WINEHQ_BRANCH}; \
    apt-get clean; \
    rm -rf /var/lib/apt/lists/*

# ── tini as PID 1 ─────────────────────────────────────────────────
RUN set -eux; \
    arch="$(dpkg --print-architecture)"; \
    wget -qO /usr/bin/tini "https://github.com/krallin/tini/releases/download/${TINI_VERSION}/tini-${arch}"; \
    wget -qO /tmp/tini.sha256 "https://github.com/krallin/tini/releases/download/${TINI_VERSION}/tini-${arch}.sha256sum"; \
    cd /tmp && sha256sum -c tini.sha256; \
    chmod +x /usr/bin/tini; \
    rm -f /tmp/tini.sha256

# ── Non-root user (matches helm/mt-node runAsUser=1000) ──────────
RUN set -eux; \
    groupadd --gid 1000 mt; \
    useradd --uid 1000 --gid 1000 --create-home --shell /bin/bash mt; \
    install -d -o mt -g mt /home/mt/.wine /home/mt/.cache /opt/ea /opt/watchdog

# ── Pre-initialise Wine prefix as user 'mt' ───────────────────────
USER mt
WORKDIR /home/mt
RUN set -eux; \
    wineboot --init 2>/dev/null || true; \
    wineserver --wait 2>/dev/null || true

# ── Download + verify MT5 installer ───────────────────────────────
USER root
RUN set -eux; \
    if [ -z "${MT5_INSTALLER_SHA256}" ]; then \
        echo "FATAL: MT5_INSTALLER_SHA256 build-arg is required. Pass --build-arg MT5_INSTALLER_SHA256=<sha256> for production builds, or 'skip' for dev." >&2; \
        exit 1; \
    fi; \
    wget -qO /tmp/mt5setup.exe "https://download.mql5.com/cdn/web/metaquotes.software.corp/mt5/mt5setup.exe"; \
    if [ "${MT5_INSTALLER_SHA256}" != "skip" ]; then \
        echo "${MT5_INSTALLER_SHA256}  /tmp/mt5setup.exe" > /tmp/mt5setup.exe.sha256; \
        sha256sum -c /tmp/mt5setup.exe.sha256; \
        rm -f /tmp/mt5setup.exe.sha256; \
    else \
        echo "WARN: MT5 installer SHA check skipped (dev mode)." >&2; \
    fi; \
    chown mt:mt /tmp/mt5setup.exe

USER mt
RUN set -eux; \
    wine /tmp/mt5setup.exe /auto 2>/dev/null || true; \
    wineserver --wait 2>/dev/null || true; \
    rm -f /tmp/mt5setup.exe

# ── Download + verify MT4 installer ───────────────────────────────
USER root
RUN set -eux; \
    if [ -z "${MT4_INSTALLER_SHA256}" ]; then \
        echo "FATAL: MT4_INSTALLER_SHA256 build-arg is required." >&2; \
        exit 1; \
    fi; \
    wget -qO /tmp/mt4setup.exe "https://download.mql5.com/cdn/web/metaquotes.software.corp/mt4/mt4setup.exe"; \
    if [ "${MT4_INSTALLER_SHA256}" != "skip" ]; then \
        echo "${MT4_INSTALLER_SHA256}  /tmp/mt4setup.exe" > /tmp/mt4setup.exe.sha256; \
        sha256sum -c /tmp/mt4setup.exe.sha256; \
        rm -f /tmp/mt4setup.exe.sha256; \
    else \
        echo "WARN: MT4 installer SHA check skipped (dev mode)." >&2; \
    fi; \
    chown mt:mt /tmp/mt4setup.exe

USER mt
RUN set -eux; \
    wine /tmp/mt4setup.exe /auto 2>/dev/null || true; \
    wineserver --wait 2>/dev/null || true; \
    rm -f /tmp/mt4setup.exe

# ── EA binaries + watchdog + entrypoint ──────────────────────────
USER root
COPY ea/ /opt/ea/
COPY watchdog.py /opt/watchdog/watchdog.py
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN set -eux; \
    chown -R mt:mt /opt/ea /opt/watchdog; \
    chmod +x /usr/local/bin/entrypoint.sh /opt/watchdog/watchdog.py

USER mt
WORKDIR /home/mt

EXPOSE 5555 9100

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/entrypoint.sh"]
