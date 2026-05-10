# ──────────────────────────────────────────────────────────────────
# etradie-mt-node — Headless MetaTrader 4/5 via Wine + Xvfb
#
# Runs on any x86/x64 Linux server. No Windows license required.
# The entrypoint.sh script reads MT_PLATFORM env var to decide
# whether to launch MT4 (terminal.exe) or MT5 (terminal64.exe).
#
# Build:  docker build -t etradie-mt-node docker/mt-node/
# ──────────────────────────────────────────────────────────────────
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    WINEDEBUG=-all \
    WINEPREFIX=/home/mt/.wine

# ── System dependencies ──────────────────────────────────────────
RUN dpkg --add-architecture i386 && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        # Wine and 32-bit runtime for MT4 compatibility
        wine64 wine32 \
        # Virtual framebuffer for headless GUI
        xvfb x11-utils \
        # Download tools
        wget ca-certificates \
        # Process management
        procps && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# ── Non-root user (security best practice) ────────────────────────
RUN useradd -m -s /bin/bash mt
USER mt
WORKDIR /home/mt

# ── Pre-initialize Wine prefix (avoids first-run GUI popups) ──────
RUN wineboot --init 2>/dev/null; \
    # Wait for wineserver to finish initializing
    wineserver --wait 2>/dev/null || true

# ── Download MetaTrader installers ────────────────────────────────
# MT5 installer (official MetaQuotes download)
RUN wget -q -O /tmp/mt5setup.exe \
    "https://download.mql5.com/cdn/web/metaquotes.software.corp/mt5/mt5setup.exe" && \
    wine /tmp/mt5setup.exe /auto 2>/dev/null; \
    wineserver --wait 2>/dev/null || true; \
    rm -f /tmp/mt5setup.exe

# MT4 installer (official MetaQuotes download)
RUN wget -q -O /tmp/mt4setup.exe \
    "https://download.mql5.com/cdn/web/metaquotes.software.corp/mt4/mt4setup.exe" && \
    wine /tmp/mt4setup.exe /auto 2>/dev/null; \
    wineserver --wait 2>/dev/null || true; \
    rm -f /tmp/mt4setup.exe

# ── EA binary placement ───────────────────────────────────────────
# Ensure the compiled binaries (ZeroMQ_EA.ex4 and ZeroMQ_EA.ex5) exist in docker/mt-node/ea/ before building.
COPY ea/ /opt/ea/
RUN chown -R mt:mt /opt/ea
USER mt

# ── Entrypoint ────────────────────────────────────────────────────
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
USER root
RUN chmod +x /usr/local/bin/entrypoint.sh
USER mt

# ZeroMQ EA listens on this port inside the container.
EXPOSE 5555

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
