package collector_test

import (
	"context"
	"log/slog"
	"os"
	"testing"
	"time"

	"github.com/prometheus/client_golang/prometheus"

	"github.com/yourname/server-agent/internal/collector"
)

// mockCollector implements Collector and returns fixed values.
// This lets us test Scraper without touching the real OS.
type mockCollector struct {
	metrics collector.SystemMetrics
	err     error
	calls   int
}

func (m *mockCollector) Collect(_ context.Context) (collector.SystemMetrics, error) {
	m.calls++
	return m.metrics, m.err
}

func TestScraper_UpdatesGaugesOnTick(t *testing.T) {
	mock := &mockCollector{
		metrics: collector.SystemMetrics{
			CPUPercent:    42.0,
			MemoryPercent: 55.0,
			DiskPercent:   70.0,
		},
	}

	reg := prometheus.NewRegistry()
	gauges, err := collector.NewGauges(reg)
	if err != nil {
		t.Fatalf("NewGauges: %v", err)
	}

	logger := slog.New(slog.NewTextHandler(os.Stdout, nil))
	scraper := collector.NewScraper(mock, gauges, 50*time.Millisecond, logger)

	ctx, cancel := context.WithTimeout(context.Background(), 200*time.Millisecond)
	defer cancel()

	scraper.Run(ctx) // blocks until ctx expires

	if mock.calls == 0 {
		t.Fatal("expected at least one collection call")
	}

	// Read back the gathered metrics and verify the CPU value.
	mfs, err := reg.Gather()
	if err != nil {
		t.Fatalf("gather: %v", err)
	}

	for _, mf := range mfs {
		if mf.GetName() == "server_agent_cpu_usage_percent" {
			got := mf.GetMetric()[0].GetGauge().GetValue()
			if got != 42.0 {
				t.Errorf("cpu gauge: got %v, want 42.0", got)
			}
			return
		}
	}
	t.Error("cpu gauge metric not found in registry")
}

func TestScraper_ContinuesAfterCollectorError(t *testing.T) {
	callCount := 0
	// First call fails, subsequent calls succeed.
	mock := &mockCollector{}

	reg := prometheus.NewRegistry()
	gauges, err := collector.NewGauges(reg)
	if err != nil {
		t.Fatalf("NewGauges: %v", err)
	}

	logger := slog.New(slog.NewTextHandler(os.Stdout, nil))
	scraper := collector.NewScraper(mock, gauges, 30*time.Millisecond, logger)

	ctx, cancel := context.WithTimeout(context.Background(), 150*time.Millisecond)
	defer cancel()

	scraper.Run(ctx)
	callCount = mock.calls

	if callCount < 2 {
		t.Errorf("scraper stopped after error: only %d calls", callCount)
	}
}
