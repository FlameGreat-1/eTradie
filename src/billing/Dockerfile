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

RUN addgroup -S etradie && adduser -S etradie -G etradie

COPY --from=builder /bin/billing /app/billing

RUN chown -R etradie:etradie /app

USER etradie

EXPOSE 8082

CMD ["/app/billing"]
