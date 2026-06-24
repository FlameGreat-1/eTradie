# syntax=docker/dockerfile:1.7
# ───────────────────────────────────────────────────────────────────
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
#
# Wine prefix layout:
#   WINEPREFIX        = /home/mt/.wine            (runtime; PVC-mounted)
#   WINE_TEMPLATE     = /opt/wine-template/.wine  (build-time bake;
#                                                  non-mounted; seeded
#                                                  into WINEPREFIX on
#                                                  first boot by
#                                                  entrypoint.sh)
# ───────────────────────────────────────────────────────────────────
FROM ubuntu:24.04

LABEL org.opencontainers.image.title="etradie-mt-node" \
      org.opencontainers.image.description="Headless MetaTrader 4/5 (Wine+Xvfb) for the eTradie self-hosted broker bridge" \
      org.opencontainers.image.vendor="eTradie" \
      org.opencontainers.image.licenses="Proprietary" \
      org.opencontainers.image.source="https://github.com/FlameGreat-1/eTradie"

# WINEPREFIX is the RUNTIME prefix path the entrypoint and watchdog
# expect (/home/mt/.wine). At image-build time we install Wine + MT5 +
# MT4 into the separate NON-MOUNTED template path
# (/opt/wine-template/.wine) so the bake is not masked by the PVC
# mount at runtime. The entrypoint then seeds /home/mt/.wine from the
# template on first boot via 'cp -a' + 'wineboot -u'.
ENV DEBIAN_FRONTEND=noninteractive \
    WINEDEBUG=-all \
    WINEPREFIX=/home/mt/.wine \
    WINE_TEMPLATE=/opt/wine-template/.wine \
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

# ── System dependencies + WineHQ apt source ─────────────────────────────────
RUN set -eux; \
    dpkg --add-architecture i386; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        ca-certificates wget gnupg apt-transport-https \
        software-properties-common procps lsof psmisc \
        xvfb x11-utils x11-apps xdotool xclip unzip \
        fluxbox \
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

# ── tini as PID 1 ───────────────────────────────────────────────────────────────────
RUN set -eux; \
    arch="$(dpkg --print-architecture)"; \
    cd /tmp; \
    wget -qO "tini-${arch}" "https://github.com/krallin/tini/releases/download/${TINI_VERSION}/tini-${arch}"; \
    wget -qO tini.sha256 "https://github.com/krallin/tini/releases/download/${TINI_VERSION}/tini-${arch}.sha256sum"; \
    sha256sum -c tini.sha256; \
    install -m 0755 "tini-${arch}" /usr/bin/tini; \
    rm -f "tini-${arch}" tini.sha256

# ── Non-root user (matches helm/mt-node runAsUser=1000) ──────────
# Ubuntu 24.04 ships a default 'ubuntu' user/group at UID/GID 1000.
# We MUST keep mt at UID/GID 1000 (helm/mt-node/values.yaml pins
# podSecurityContext.runAsUser=1000) so delete the default user first.
# `|| true` keeps the step idempotent if a future base image drops the
# default account.
RUN set -eux; \
    userdel -r ubuntu 2>/dev/null || true; \
    groupdel ubuntu 2>/dev/null || true; \
    groupadd --gid 1000 mt; \
    useradd --uid 1000 --gid 1000 --create-home --shell /bin/bash mt; \
    install -d -o mt -g mt \
        /home/mt/.wine \
        /home/mt/.cache \
        /opt/ea \
        /opt/watchdog \
        /opt/wine-template \
        /opt/wine-template/.wine

# ── Pre-initialise Wine prefix as user 'mt' INTO THE TEMPLATE PATH ────
# The wineboot here MUST target the template path (WINEPREFIX override),
# not the runtime /home/mt/.wine path. At runtime the PVC mounts at
# /home/mt/.wine and masks anything baked there - so the bake has to
# live somewhere the PVC can't see, and the entrypoint seeds the PVC
# from this template on first boot via 'cp -a' + 'wineboot -u'.
USER mt
WORKDIR /home/mt
RUN set -eux; \
    WINEPREFIX="$WINE_TEMPLATE" wineboot --init 2>/dev/null || true; \
    WINEPREFIX="$WINE_TEMPLATE" wineserver --wait 2>/dev/null || true

# ── Install MT5 from a PRE-INSTALLED PORTABLE artifact ──────────────────────
# MT5_INSTALLER_URL points at a .zip of an already-installed MetaTrader 5
# directory (generated once on a Wine+Xvfb host and hosted on an anonymous
# HTTPS bucket, e.g. Cloudflare R2). We do NOT run mtXsetup.exe at build
# time: that installer is an interactive GUI web-installer that either
# silently no-ops without a display or HANGS forever under xvfb waiting on a
# prompt (defect #13). Download -> sha256 verify -> unzip is deterministic,
# reproducible, and cannot hang. The zip carries a top-level `MetaTrader 5`
# directory, so unzipping into 'Program Files/' yields
# 'Program Files/MetaTrader 5/terminal64.exe'.
USER root
RUN set -eux; \
    if [ -z "${MT5_INSTALLER_SHA256}" ]; then \
        echo "FATAL: MT5_INSTALLER_SHA256 build-arg is required. Pass --build-arg MT5_INSTALLER_SHA256=<sha256-of-the-portable-zip> for production builds, or 'skip' for dev." >&2; \
        exit 1; \
    fi; \
    MT5_DEST="$WINE_TEMPLATE/drive_c/Program Files"; \
    MT5_EXE="$MT5_DEST/MetaTrader 5/terminal64.exe"; \
    if [ "${MT5_INSTALLER_SHA256}" = "skip" ]; then \
        echo "WARN: MT5_INSTALLER_SHA256=skip - skipping MT5 portable download/unzip (dev mode; image will NOT run a real MT5)." >&2; \
    else \
        wget -qO /tmp/mt5-portable.zip "${MT5_INSTALLER_URL}"; \
        echo "${MT5_INSTALLER_SHA256}  /tmp/mt5-portable.zip" > /tmp/mt5-portable.zip.sha256; \
        sha256sum -c /tmp/mt5-portable.zip.sha256; \
        rm -f /tmp/mt5-portable.zip.sha256; \
        mkdir -p "$MT5_DEST"; \
        unzip -q -o /tmp/mt5-portable.zip -d "$MT5_DEST"; \
        rm -f /tmp/mt5-portable.zip; \
        if [ ! -f "$MT5_EXE" ]; then \
            echo "FATAL: MT5 portable unzipped but terminal64.exe is missing at '$MT5_EXE'. The zip layout is wrong (expected a top-level 'MetaTrader 5/' dir). Failing the build instead of shipping a broken image." >&2; \
            exit 1; \
        fi; \
        echo "INFO: MT5 terminal64.exe verified at '$MT5_EXE'." >&2; \
    fi

# ── Install MT4 from a PRE-INSTALLED PORTABLE artifact ──────────────────────
# Same deterministic download+verify+unzip as MT5 above. MT4 is a 32-bit
# app and installs into the 'Program Files (x86)' tree; the zip carries a
# top-level `MetaTrader 4` dir so unzipping into 'Program Files (x86)/'
# yields 'Program Files (x86)/MetaTrader 4/terminal.exe'.
USER root
RUN set -eux; \
    if [ -z "${MT4_INSTALLER_SHA256}" ]; then \
        echo "FATAL: MT4_INSTALLER_SHA256 build-arg is required. Pass --build-arg MT4_INSTALLER_SHA256=<sha256-of-the-portable-zip> for production builds, or 'skip' for dev." >&2; \
        exit 1; \
    fi; \
    MT4_DEST="$WINE_TEMPLATE/drive_c/Program Files (x86)"; \
    MT4_EXE="$MT4_DEST/MetaTrader 4/terminal.exe"; \
    if [ "${MT4_INSTALLER_SHA256}" = "skip" ]; then \
        echo "WARN: MT4_INSTALLER_SHA256=skip - skipping MT4 portable download/unzip (dev mode; image will NOT run a real MT4)." >&2; \
    else \
        wget -qO /tmp/mt4-portable.zip "${MT4_INSTALLER_URL}"; \
        echo "${MT4_INSTALLER_SHA256}  /tmp/mt4-portable.zip" > /tmp/mt4-portable.zip.sha256; \
        sha256sum -c /tmp/mt4-portable.zip.sha256; \
        rm -f /tmp/mt4-portable.zip.sha256; \
        mkdir -p "$MT4_DEST"; \
        unzip -q -o /tmp/mt4-portable.zip -d "$MT4_DEST"; \
        rm -f /tmp/mt4-portable.zip; \
        if [ ! -f "$MT4_EXE" ]; then \
            echo "FATAL: MT4 portable unzipped but terminal.exe is missing at '$MT4_EXE'. The zip layout is wrong (expected a top-level 'MetaTrader 4/' dir). Failing the build instead of shipping a broken image." >&2; \
            exit 1; \
        fi; \
        echo "INFO: MT4 terminal.exe verified at '$MT4_EXE'." >&2; \
    fi; \
    # Single ownership sweep for the whole template: this runs after BOTH
    # the MT5 and MT4 unzips above, so the runtime 'mt' user (uid 1000)
    # owns every file under $WINE_TEMPLATE. The entrypoint seeds the
    # PVC-mounted prefix from here on first boot (see entrypoint.sh).
    chown -R mt:mt "$WINE_TEMPLATE"

# ── EA binaries + watchdog + entrypoint ─────────────────────────
USER root
COPY ea/ /opt/ea/
COPY watchdog.py /opt/watchdog/watchdog.py
COPY entrypoint.sh /usr/local/bin/entrypoint.sh

# ── Bake EA Dependencies into Wine Template ─────────────────────
COPY ea/deps/ /tmp/ea_deps/

RUN set -eux; \
    MT5_ROOT="$WINE_TEMPLATE/drive_c/Program Files/MetaTrader 5"; \
    MT4_ROOT="$WINE_TEMPLATE/drive_c/Program Files (x86)/MetaTrader 4"; \
    # The portable MT zips are generated from a fresh install that has
    # not yet created the MQL Libraries/Include trees (the terminal
    # creates them on first run/compile). Create them so the EA dep
    # copies below cannot fail with 'No such file or directory'.
    mkdir -p "$MT5_ROOT/MQL5/Libraries" "$MT5_ROOT/MQL5/Include" \
             "$MT4_ROOT/MQL4/Libraries" "$MT4_ROOT/MQL4/Include"; \
    cp /tmp/ea_deps/mt5/libzmq.dll "$MT5_ROOT/MQL5/Libraries/libzmq.dll"; \
    cp /tmp/ea_deps/mt4/libzmq.dll "$MT4_ROOT/MQL4/Libraries/libzmq.dll"; \
    cp -r /tmp/ea_deps/Include/Zmq "$MT5_ROOT/MQL5/Include/Zmq"; \
    cp -r /tmp/ea_deps/Include/Zmq "$MT4_ROOT/MQL4/Include/Zmq"; \
    cp /tmp/ea_deps/Include/JAson.mqh "$MT5_ROOT/MQL5/Include/JAson.mqh"; \
    cp /tmp/ea_deps/Include/JAson.mqh "$MT4_ROOT/MQL4/Include/JAson.mqh"; \
    rm -rf /tmp/ea_deps; \
    if [ ! -f "$WINE_TEMPLATE/drive_c/Program Files/MetaTrader 5/MQL5/Libraries/libzmq.dll" ]; then \
        echo "FATAL: libzmq.dll missing in MT5 template" >&2; \
        exit 1; \
    fi; \
    if [ ! -f "$WINE_TEMPLATE/drive_c/Program Files (x86)/MetaTrader 4/MQL4/Libraries/libzmq.dll" ]; then \
        echo "FATAL: libzmq.dll missing in MT4 template" >&2; \
        exit 1; \
    fi; \
    # Defect #15: bake LiveUpdate-neutralization into the template so a
    # freshly-seeded prefix ships with the updater disabled on first
    # boot.
    #
    # PROVEN (staging, build 5836; see
    # docs/runbooks/HOSTED-MT-PROVISIONING-SESSION.md): the
    # [LiveUpdate] LastBuildDataPath key in terminal.ini does NOT stop
    # LiveUpdate -- it was present in the exact terminal.ini the
    # terminal reads and the terminal still downloaded mt5onnx64 and
    # self-restarted (exit 143) in an infinite loop. It is retained
    # below ONLY as a harmless tertiary, NOT as the mechanism.
    #
    # DEAD END -- the common.ini [Common] Source= neutralization was
    # tried (baked here + re-asserted in entrypoint.sh) and is
    # empirically DISPROVEN: MT5 build 5836 still downloaded mt5onnx64
    # and self-restarted (see runbook). It has been REMOVED. The only
    # working LiveUpdate control is the per-tenant NetworkPolicy egress
    # block (runbook Layer 2), not any baked config.
    #
    # The terminal.ini LastBuildDataPath pin below is likewise INEFFECTIVE
    # (proven), retained only as inert legacy so the seeded prefix shape
    # is unchanged. Do not add a common.ini 'fix' here again.
    mkdir -p "$MT5_ROOT/config" "$MT4_ROOT/config"; \
    printf '[LiveUpdate]\nLastBuildDataPath=5836\n' > "$MT5_ROOT/config/terminal.ini"; \
    printf '[LiveUpdate]\nLastBuildDataPath=5836\n' > "$MT4_ROOT/config/terminal.ini"; \
    if ! grep -q 'LastBuildDataPath' "$MT5_ROOT/config/terminal.ini"; then \
        echo "FATAL: LiveUpdate pin missing in MT5 template terminal.ini" >&2; \
        exit 1; \
    fi; \
    if ! grep -q 'LastBuildDataPath' "$MT4_ROOT/config/terminal.ini"; then \
        echo "FATAL: LiveUpdate pin missing in MT4 template terminal.ini" >&2; \
        exit 1; \
    fi

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
    chown -R mt:mt /opt/ea /opt/watchdog "$WINE_TEMPLATE"; \
    chmod +x /usr/local/bin/entrypoint.sh /opt/watchdog/watchdog.py

# NOTE: the Wine template ownership sweep is done in the MT4 install step
# above (it runs after both MT5 and MT4 unzip into $WINE_TEMPLATE), so no
# separate `chown -R /opt/wine-template` is needed here.
USER mt
WORKDIR /home/mt

EXPOSE 5555 9100

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/entrypoint.sh"]
