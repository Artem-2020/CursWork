# ── build stage ────────────────────────────────────────────────────────────────
FROM golang:1.22-alpine AS builder

WORKDIR /src

# Cache dependency downloads separately from source compilation.
COPY go.mod go.sum ./
RUN go mod download

COPY . .

RUN CGO_ENABLED=0 GOOS=linux go build \
    -ldflags="-s -w" \
    -o /bin/agent \
    ./cmd/agent

# ── final stage ────────────────────────────────────────────────────────────────
FROM scratch

# Copy only the compiled binary — no shell, no package manager.
COPY --from=builder /bin/agent /agent

# Prometheus default scrape port.
EXPOSE 9100

ENTRYPOINT ["/agent"]
