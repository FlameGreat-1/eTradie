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

# Non-root user for security
RUN addgroup -S etradie && adduser -S etradie -G etradie

# Copy over the static binary
COPY --from=builder /bin/gateway /app/gateway

# Make etradie user own the folder
RUN chown -R etradie:etradie /app

USER etradie

EXPOSE 8080 50052

CMD ["/app/gateway"]
