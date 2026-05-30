# syntax=docker/dockerfile:1.7
# ──────────────────────────────────────────────────────────────────
# etradie-mt-node — Headless MetaTrader 4/5 via Wine + Xvfb
#
# Runs on any x86_64 Linux. No Windows license required.
#
# Build (production, full supply-chain pinning):
#   docker build \
#     --build-arg MT5_INSTALLER_SHA256=<sha256-from-mql5.com> \
#     --build-arg MT4_INSTALLER_SHA256=<sha256-from-mql5.com> \
#     --build-arg EA_EX5_SHA256=<sha256-of-docker/mt-node/ea/ZeroMQ_EA.ex5> \
#     --build-arg EA_EX4_SHA256=<sha256-of-docker/mt-node/ea/ZeroMQ_EA.ex4> \
#     -t ghcr.io/flamegreat-1/etradie-mt-node:0.1.0 \
#     docker/mt-node/
#
# Build (production, offline / air-gapped mirror):
#   docker build \
#     --build-arg MT5_INSTALLER_URL=https://artifactory.example.com/mql5/mt5setup-v5.0.123.exe \
#     --build-arg MT5_INSTALLER_SHA256=<sha-of-that-blob> \
#     --build-arg MT4_INSTALLER_URL=https://artifactory.example.com/mql5/mt4setup-v4.0.123.exe \
#     --build-arg MT4_INSTALLER_SHA256=<sha-of-that-blob> \
#     --build-arg EA_EX5_SHA256=<...> --build-arg EA_EX4_SHA256=<...> \
#     -t ghcr.io/flamegreat-1/etradie-mt-node:0.1.0 \
#     docker/mt-node/
#
# Build (dev, SKIP all SHA enforcement — NOT for production):
#   docker build \
#     --build-arg MT5_INSTALLER_SHA256=skip \
#     --build-arg MT4_INSTALLER_SHA256=skip \
#     --build-arg EA_EX5_SHA256=skip \
#     --build-arg EA_EX4_SHA256=skip \
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

# Supply-chain build-arg gates. Empty -> build fails. "skip" -> dev-only.
ARG MT5_INSTALLER_SHA256=""
ARG MT4_INSTALLER_SHA256=""
ARG MT5_INSTALLER_URL="https://download.mql5.com/cdn/web/metaquotes.software.corp/mt5/mt5setup.exe"
ARG MT4_INSTALLER_URL="https://download.mql5.com/cdn/web/metaquotes.software.corp/mt4/mt4setup.exe"
ARG EA_EX5_SHA256=""
ARG EA_EX4_SHA256=""
ARG TINI_VERSION=v0.19.0
ARG WINEHQ_BRANCH=stable
# WINEHQ_VERSION pins the EXACT apt version string for every winehq-*
# package. Production CI MUST set this; dev builds may leave it empty
# (the build then prints a loud WARN). The canonical way to discover
# the current pin value is to run apt-cache policy winehq-stable
# inside a fresh ubuntu:24.04 container with the winehq apt source
# configured. The snippet lives in docker/mt-node/README.md.
#
# Pin BOTH the meta-package (winehq-${WINEHQ_BRANCH}) AND the
# sub-packages (wine-${WINEHQ_BRANCH}, wine-${WINEHQ_BRANCH}-amd64,
# wine-${WINEHQ_BRANCH}-i386) to the same version string. Otherwise
# apt resolves the meta-package's deps freely on every build and
# the pin is effectively cosmetic.
ARG WINEHQ_VERSION=""

# ── System dependencies + WineHQ apt source ───────────────────────────────
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
    # WineHQ packages explicitly need their Recommends (libs for
    # 32-bit support, mesa, freetype variants, etc.). The previous
    # Dockerfile carried both --no-install-recommends and
    # --install-recommends on the same line; apt's last-flag-wins
    # meant Recommends were always installed but the intent was
    # unclear. Spell out the correct flag.
    if [ -z "${WINEHQ_VERSION}" ]; then \
        echo "FATAL: WINEHQ_VERSION build-arg is required. Pass --build-arg WINEHQ_VERSION=<apt-version-string> for production builds (run 'apt-cache policy winehq-stable' to discover the current value), or 'skip' for dev." >&2; \
        exit 1; \
    fi; \
    if [ "${WINEHQ_VERSION}" = "skip" ]; then \
        echo "WARN: WINEHQ_VERSION=skip - Wine will install at whatever winehq-${WINEHQ_BRANCH} resolves to today. NOT a reproducible build; dev only." >&2; \
        apt-get install -y --install-recommends winehq-${WINEHQ_BRANCH}; \
    else \
        echo "INFO: pinning winehq-${WINEHQ_BRANCH} to version ${WINEHQ_VERSION}" >&2; \
        apt-get install -y --install-recommends \
            winehq-${WINEHQ_BRANCH}=${WINEHQ_VERSION} \
            wine-${WINEHQ_BRANCH}=${WINEHQ_VERSION} \
            wine-${WINEHQ_BRANCH}-amd64=${WINEHQ_VERSION} \
            wine-${WINEHQ_BRANCH}-i386=${WINEHQ_VERSION}; \
        apt-mark hold \
            winehq-${WINEHQ_BRANCH} \
            wine-${WINEHQ_BRANCH} \
            wine-${WINEHQ_BRANCH}-amd64 \
            wine-${WINEHQ_BRANCH}-i386; \
    fi; \
    apt-get clean; \
    rm -rf /var/lib/apt/lists/*

# ── tini as PID 1 ──────────────────────────────────────────────────────────────
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

# ── Pre-initialise Wine prefix as user 'mt' ──────────────────────
USER mt
WORKDIR /home/mt
RUN set -eux; \
    wineboot --init 2>/dev/null || true; \
    wineserver --wait 2>/dev/null || true

# ── Download + verify MT5 installer ────────────────────────────────────
USER root
RUN set -eux; \
    if [ -z "${MT5_INSTALLER_SHA256}" ]; then \
        echo "FATAL: MT5_INSTALLER_SHA256 build-arg is required. Pass --build-arg MT5_INSTALLER_SHA256=<sha256> for production builds, or 'skip' for dev." >&2; \
        exit 1; \
    fi; \
    wget -qO /tmp/mt5setup.exe "${MT5_INSTALLER_URL}"; \
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

# ── Download + verify MT4 installer ────────────────────────────────────
USER root
RUN set -eux; \
    if [ -z "${MT4_INSTALLER_SHA256}" ]; then \
        echo "FATAL: MT4_INSTALLER_SHA256 build-arg is required." >&2; \
        exit 1; \
    fi; \
    wget -qO /tmp/mt4setup.exe "${MT4_INSTALLER_URL}"; \
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

# ── EA binaries + watchdog + entrypoint ───────────────────────────────
USER root
COPY ea/ /opt/ea/
COPY watchdog.py /opt/watchdog/watchdog.py
COPY entrypoint.sh /usr/local/bin/entrypoint.sh

# Verify EA binary SHAs. A backdoored .ex5 that quietly replaces the
# committed file would deploy on every Pod without this check.
# 'skip' is dev-only - production CI MUST pass real values.
RUN set -eux; \
    if [ -z "${EA_EX5_SHA256}" ]; then \
        echo "FATAL: EA_EX5_SHA256 build-arg is required. Run 'make mt-node-ea-sha' to compute, or pass 'skip' for dev." >&2; \
        exit 1; \
    fi; \
    if [ "${EA_EX5_SHA256}" != "skip" ] && [ -f /opt/ea/ZeroMQ_EA.ex5 ]; then \
        echo "${EA_EX5_SHA256}  /opt/ea/ZeroMQ_EA.ex5" > /tmp/ea_ex5.sha256; \
        sha256sum -c /tmp/ea_ex5.sha256; \
        rm -f /tmp/ea_ex5.sha256; \
    else \
        echo "WARN: EA .ex5 SHA check skipped (dev mode or file missing)." >&2; \
    fi; \
    if [ -z "${EA_EX4_SHA256}" ]; then \
        echo "FATAL: EA_EX4_SHA256 build-arg is required." >&2; \
        exit 1; \
    fi; \
    if [ "${EA_EX4_SHA256}" != "skip" ] && [ -f /opt/ea/ZeroMQ_EA.ex4 ]; then \
        echo "${EA_EX4_SHA256}  /opt/ea/ZeroMQ_EA.ex4" > /tmp/ea_ex4.sha256; \
        sha256sum -c /tmp/ea_ex4.sha256; \
        rm -f /tmp/ea_ex4.sha256; \
    else \
        echo "WARN: EA .ex4 SHA check skipped (dev mode or file missing)." >&2; \
    fi; \
    chown -R mt:mt /opt/ea /opt/watchdog; \
    chmod +x /usr/local/bin/entrypoint.sh /opt/watchdog/watchdog.py

USER mt
WORKDIR /home/mt

EXPOSE 5555 9100

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/entrypoint.sh"]
