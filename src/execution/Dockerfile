# ── Build stage ──────────────────────────────────────────────────
FROM golang:1.22-alpine AS builder

WORKDIR /src

# Install essential build dependencies
RUN apk add --no-cache git ca-certificates tzdata make

# Cache dependencies
COPY go.mod go.sum ./
RUN go mod download

# Copy the source code
COPY . .

# Build the Execution Engine binary statically
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 \
    go build -trimpath -ldflags="-s -w -extldflags '-static'" \
    -o /bin/execution ./src/execution/cmd/execution

# ── Runtime stage ────────────────────────────────────────────────
FROM alpine:3.19 AS runtime

RUN apk --no-cache add ca-certificates tzdata \
    && rm -rf /var/cache/apk/*

WORKDIR /app

# Non-root user setup
RUN addgroup -S etradie && adduser -S etradie -G etradie

# Copy over the static binary
COPY --from=builder /bin/execution /app/execution

RUN chown -R etradie:etradie /app

USER etradie

# Internal ports
EXPOSE 8080 50053

CMD ["/app/execution"]
