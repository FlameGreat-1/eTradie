# ── Build stage ──────────────────────────────────────────────────
FROM golang:1.25-alpine AS builder

WORKDIR /src

# Install essential build dependencies
RUN apk add --no-cache git ca-certificates tzdata make

# Cache dependencies
COPY go.mod go.sum* ./
RUN go mod download

# Copy the source code
COPY . .

# Build the Management Engine binary statically
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 \
    go build -trimpath -ldflags="-s -w -extldflags '-static'" \
    -o /bin/management ./src/management/cmd/management

# ── Runtime stage ────────────────────────────────────────────────
FROM alpine:3.24 AS runtime

RUN apk --no-cache add ca-certificates tzdata \
    && rm -rf /var/cache/apk/*

WORKDIR /app

# Copy over the static binary, owned by the numeric UID/GID the Helm
# chart pins in securityContext.runAsUser/runAsGroup (65532).
COPY --from=builder --chown=65532:65532 /bin/management /app/management

# Numeric, deterministic non-root user matching the chart.
USER 65532:65532

# Internal ports: gRPC=50054, HTTP=8083
EXPOSE 8083 50054

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8083/health || exit 1

CMD ["/app/management"]
