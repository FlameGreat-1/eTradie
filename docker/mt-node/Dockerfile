# syntax=docker/dockerfile:1.7
# ───────────────────────────────────────────────────────────────────
# etradie-mt-node — Headless MetaTrader 4/5 via Wine + Xvfb
#
# Runs on any x86_64 Linux. No Windows license required.
#
# Architecture
# ------------
# The image carries Wine + Xvfb + fluxbox + xdotool + EA binaries +
# the watchdog sidecar. It does NOT carry a MetaTrader install.
# Every per-tenant Pod receives the broker-specific MT install at
# runtime via the broker-bundle initContainer:
#
#   1. The engine provisioner (src/engine/ta/broker/mt5/hosted/
#      provisioner.py) and the helm chart (helm/mt-node/templates/
#      statefulset.yaml) attach an initContainer that downloads the
#      per-broker portable zip from R2, verifies its sha256, and
#      unpacks it into an emptyDir volume mounted at /broker-bundle.
#   2. entrypoint.sh detects the branded MT root inside
#      /broker-bundle/, overlays its full tree onto $MT_DIR (a
#      subdirectory of the per-tenant Wine-prefix PVC), installs the
#      EA binary + libzmq.dll + EA Include headers AFTER the overlay,
#      writes per-tenant startup.ini + chart template, and launches
#      the BRANDED terminal64.exe / terminal.exe from $MT_DIR.
#
# Build (production, supply-chain pinning):
#   docker build \
#     --build-arg WINEHQ_VERSION=<apt-version-string> \
#     --build-arg EA_EX5_SHA256=<sha256-of-docker/mt-node/ea/ZeroMQ_EA.ex5> \
#     --build-arg EA_EX4_SHA256=<sha256-of-docker/mt-node/ea/ZeroMQ_EA.ex4> \
#     -t ghcr.io/<your-org>/etradie-mt-node:0.1.0 \
#     docker/mt-node/
#
# Build (dev, SKIP all SHA enforcement — NOT for production):
#   docker build \
#     --build-arg WINEHQ_VERSION=skip \
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
#   BUNDLE_R2_PATH, BUNDLE_SHA256 (per-tenant broker bundle pin)
#
# Wine prefix layout:
#   WINEPREFIX        = /home/mt/.wine                (mount-point;
#                                                      runtime PVC root)
#   WINEPREFIX/prefix = the Wine prefix the entrypoint uses
#                       (sub-dir; entrypoint mkdir's it as uid 1000)
#   WINE_TEMPLATE     = /opt/wine-template/.wine      (build-time bake:
#                       wineboot --init only, NO MT5/MT4 install; the
#                       entrypoint seeds the PVC-mounted prefix from
#                       this on first boot, then the broker-bundle
#                       initContainer's overlay installs MT)
# ───────────────────────────────────────────────────────────────────
FROM ubuntu:26.04

LABEL org.opencontainers.image.title="etradie-mt-node" \
      org.opencontainers.image.description="Headless MetaTrader 4/5 (Wine+Xvfb) for the eTradie self-hosted broker bridge. Runtime overlay model: the image carries no MT install; per-tenant branded MT is delivered at pod boot via the broker-bundle initContainer." \
      org.opencontainers.image.vendor="eTradie" \
      org.opencontainers.image.licenses="Proprietary" \
      org.opencontainers.image.source="https://github.com/FlameGreat-1/eTradie"

# WINEPREFIX is the RUNTIME prefix path the entrypoint and watchdog
# expect (/home/mt/.wine). At image-build time we initialise Wine
# (no MT install) into the separate NON-MOUNTED template path
# (/opt/wine-template/.wine) so the bake is not masked by the PVC
# mount at runtime. The entrypoint then seeds /home/mt/.wine from the
# template on first boot via 'cp -a' + 'wineboot -u', and the broker-
# bundle overlay (entrypoint.sh) installs the BRANDED terminal64.exe
# afterwards.
ENV DEBIAN_FRONTEND=noninteractive \
    WINEDEBUG=-all \
    WINEPREFIX=/home/mt/.wine \
    WINE_TEMPLATE=/opt/wine-template/.wine \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# Supply-chain build-arg gates. Empty -> build fails. "skip" -> dev-only.
# The MT5/MT4 installer ARGs are intentionally absent: the image no
# longer downloads any MT installer at build time. Branded MT is
# delivered at runtime via the broker-bundle initContainer (R2 pin in
# infrastructure/broker-catalog/<brand>.json).
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
        /opt/ea/deps \
        /opt/watchdog \
        /opt/wine-template \
        /opt/wine-template/.wine

# ── Pre-initialise Wine prefix as user 'mt' INTO THE TEMPLATE PATH ────
# The wineboot here MUST target the template path (WINEPREFIX override),
# not the runtime /home/mt/.wine path. At runtime the PVC mounts at
# /home/mt/.wine and masks anything baked there - so the bake has to
# live somewhere the PVC can't see, and the entrypoint seeds the PVC
# from this template on first boot via 'cp -a' + 'wineboot -u'.
#
# This step does NOT install MetaTrader. MT lands at runtime via the
# broker-bundle initContainer's overlay (entrypoint.sh).
USER mt
WORKDIR /home/mt
RUN set -eux; \
    WINEPREFIX="$WINE_TEMPLATE" wineboot --init 2>/dev/null || true; \
    WINEPREFIX="$WINE_TEMPLATE" wineserver --wait 2>/dev/null || true; \
    # Sanity: every later step in the pipeline relies on system32
    # existing in the template; entrypoint.sh uses its absence as the
    # ONLY real corruption signal. Fail the build if wineboot did not
    # produce it.
    if [ ! -d "$WINE_TEMPLATE/drive_c/windows/system32" ]; then \
        echo "FATAL: wineboot --init did not produce drive_c/windows/system32 in $WINE_TEMPLATE; aborting build." >&2; \
        exit 1; \
    fi

# ── EA binaries + dependencies + watchdog + entrypoint ─────────────
# /opt/ea/      → ZeroMQ_EA.ex{5,4} (EA binaries verified by SHA below)
# /opt/ea/deps → libzmq.dll + Include/{Zmq,JAson.mqh} for installation
#                into the BRANDED MT root by entrypoint.sh AFTER the
#                broker-bundle overlay lands.
USER root
COPY ea/ /opt/ea/
COPY watchdog.py /opt/watchdog/watchdog.py
COPY entrypoint.sh /usr/local/bin/entrypoint.sh

# Move the EA deps subtree from the bundled COPY (ea/deps/...) into
# the runtime install staging dir (/opt/ea/deps). entrypoint.sh expects:
#   /opt/ea/deps/mt5/libzmq.dll
#   /opt/ea/deps/mt4/libzmq.dll
#   /opt/ea/deps/Include/Zmq/...
#   /opt/ea/deps/Include/JAson.mqh
# These are installed into the BRANDED MT root after the bundle overlay.
RUN set -eux; \
    if [ ! -d /opt/ea/deps ]; then \
        echo "FATAL: /opt/ea/deps not present; the COPY of ea/deps/ failed or the layout changed." >&2; \
        exit 1; \
    fi; \
    for f in /opt/ea/deps/mt5/libzmq.dll \
             /opt/ea/deps/mt4/libzmq.dll \
             /opt/ea/deps/Include/JAson.mqh; do \
        if [ ! -f "$f" ]; then \
            echo "FATAL: missing required EA dep at $f" >&2; \
            exit 1; \
        fi; \
    done; \
    if [ ! -d /opt/ea/deps/Include/Zmq ]; then \
        echo "FATAL: missing required EA dep dir /opt/ea/deps/Include/Zmq" >&2; \
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

USER mt
WORKDIR /home/mt

EXPOSE 5555 9100

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/entrypoint.sh"]
