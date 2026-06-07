# ── Build stage ──────────────────────────────────────────────────
FROM golang:1.23-alpine AS builder

WORKDIR /src

RUN apk add --no-cache git ca-certificates tzdata make

COPY go.mod go.sum* ./
RUN go mod download

COPY . .

RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 \
    go build -trimpath -ldflags="-s -w -extldflags '-static'" \
    -o /bin/billing ./src/billing/cmd/server

# ── Runtime stage ────────────────────────────────────────────────
FROM alpine:3.19 AS runtime

RUN apk --no-cache add ca-certificates tzdata \
    && rm -rf /var/cache/apk/*

WORKDIR /app

# Copy over the static binary, owned by the numeric UID/GID the Helm
# chart pins in securityContext.runAsUser/runAsGroup (65532).
COPY --from=builder --chown=65532:65532 /bin/billing /app/billing

# Numeric, deterministic non-root user matching the chart.
USER 65532:65532

EXPOSE 8082

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8082/health || exit 1

CMD ["/app/billing"]
