# ── Build stage ──────────────────────────────────────────────────
FROM golang:1.23-alpine AS builder

WORKDIR /src

# Install essential build dependencies
RUN apk add --no-cache git ca-certificates tzdata make

# Cache dependencies
COPY go.mod go.sum* ./
RUN go mod download

# Copy the source code
COPY . .

# Build the Gateway binary statically
# Using CGO_ENABLED=0 to ensure a scratch-compatible binary
# -s -w removes DWARF debugging info to heavily compress the binary
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 \
    go build -trimpath -ldflags="-s -w -extldflags '-static'" \
    -o /bin/gateway ./src/gateway/cmd/gateway

# ── Runtime stage ────────────────────────────────────────────────
FROM alpine:3.19 AS runtime

# Install CA certificates and timezone data for secure HTTPS and correct logging
RUN apk --no-cache add ca-certificates tzdata \
    && rm -rf /var/cache/apk/*

WORKDIR /app

# Copy over the static binary, owned by the numeric UID/GID the Helm
# chart pins in securityContext.runAsUser/runAsGroup (65532).
COPY --from=builder --chown=65532:65532 /bin/gateway /app/gateway

# Numeric, deterministic non-root user matching the chart. Using the
# raw UID:GID avoids depending on a named user existing in the image.
USER 65532:65532

EXPOSE 8080 50052

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8080/health || exit 1

CMD ["/app/gateway"]
