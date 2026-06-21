package server

import (
    "context"
    "io"
    "log/slog"
    "net/http"
    "net/http/httptest"
    "testing"
    "time"

    "github.com/prometheus/client_golang/prometheus"
)

func TestHealthzHandler(t *testing.T) {
    req := httptest.NewRequest("GET", "/healthz", nil)
    w := httptest.NewRecorder()

    healthzHandler(w, req)

    resp := w.Result()
    body, _ := io.ReadAll(resp.Body)

    if resp.StatusCode != http.StatusOK {
        t.Errorf("expected 200, got %d", resp.StatusCode)
    }
    if string(body) != "ok" {
        t.Errorf("expected 'ok', got %s", string(body))
    }
}

func TestNewServer(t *testing.T) {
    reg := prometheus.NewRegistry()
    logger := slog.New(slog.NewTextHandler(io.Discard, nil))

    srv := New(":9999", reg, logger)

    if srv.httpServer.Addr != ":9999" {
        t.Errorf("expected :9999, got %s", srv.httpServer.Addr)
    }
    if srv.httpServer.Handler == nil {
        t.Error("handler should not be nil")
    }
}

func TestMetricsEndpoint(t *testing.T) {
    reg := prometheus.NewRegistry()
    logger := slog.New(slog.NewTextHandler(io.Discard, nil))

    gauge := prometheus.NewGauge(prometheus.GaugeOpts{
        Name: "test_metric",
        Help: "Test metric",
    })
    reg.MustRegister(gauge)
    gauge.Set(42.0)

    srv := New(":0", reg, logger)

    ts := httptest.NewServer(srv.httpServer.Handler)
    defer ts.Close()

    resp, err := http.Get(ts.URL + "/metrics")
    if err != nil {
        t.Fatalf("failed to get metrics: %v", err)
    }
    defer resp.Body.Close()

    if resp.StatusCode != http.StatusOK {
        t.Errorf("expected 200, got %d", resp.StatusCode)
    }

    body, _ := io.ReadAll(resp.Body)
    if !contains(string(body), "test_metric") {
        t.Error("metrics endpoint did not return test_metric")
    }
}

func TestServerGracefulShutdown(t *testing.T) {
    reg := prometheus.NewRegistry()
    logger := slog.New(slog.NewTextHandler(io.Discard, nil))

    srv := New(":0", reg, logger)

    ctx, cancel := context.WithCancel(context.Background())

    errCh := make(chan error, 1)
    go func() {
        errCh <- srv.ListenAndServe(ctx)
    }()

    time.Sleep(100 * time.Millisecond)
    cancel()

    select {
    case err := <-errCh:
        if err != nil && err.Error() != "http: Server closed" {
            t.Errorf("unexpected error: %v", err)
        }
    case <-time.After(2 * time.Second):
        t.Error("server did not shut down gracefully")
    }
}

func TestServerListenAndServeWithInvalidPort(t *testing.T) {
    reg := prometheus.NewRegistry()
    logger := slog.New(slog.NewTextHandler(io.Discard, nil))

    srv := New(":99999", reg, logger)

    ctx := context.Background()

    errCh := make(chan error, 1)
    go func() {
        errCh <- srv.ListenAndServe(ctx)
    }()

    select {
    case err := <-errCh:
        if err == nil {
            t.Error("expected error for invalid port, got nil")
        }
    case <-time.After(1 * time.Second):
        t.Error("timeout: ListenAndServe did not return error")
    }
}

func contains(s, substr string) bool {
    for i := 0; i <= len(s)-len(substr); i++ {
        if s[i:i+len(substr)] == substr {
            return true
        }
    }
    return false
}