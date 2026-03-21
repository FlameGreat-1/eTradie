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

# Build the Management Engine binary statically
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 \
    go build -trimpath -ldflags="-s -w -extldflags '-static'" \
    -o /bin/management ./src/management/cmd/management

# ── Runtime stage ────────────────────────────────────────────────
FROM alpine:3.19 AS runtime

RUN apk --no-cache add ca-certificates tzdata \
    && rm -rf /var/cache/apk/*

WORKDIR /app

# Non-root user setup
RUN addgroup -S etradie && adduser -S etradie -G etradie

# Copy over the static binary
COPY --from=builder /bin/management /app/management

RUN chown -R etradie:etradie /app

USER etradie

# Internal ports: gRPC=50054, HTTP=8083
EXPOSE 8083 50054

CMD ["/app/management"]
