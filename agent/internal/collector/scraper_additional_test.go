package collector

import (
	"context"
	"errors"
	"log/slog"
	"os"
	"testing"
	"time"

	"github.com/prometheus/client_golang/prometheus"
)

type testMockCollector struct {
	metrics SystemMetrics
	err     error
	calls   int
}

func (m *testMockCollector) Collect(_ context.Context) (SystemMetrics, error) {
	m.calls++
	return m.metrics, m.err
}

func TestScraper_NewScraper(t *testing.T) {
	mock := &testMockCollector{}
	reg := prometheus.NewRegistry()
	gauges, _ := NewGauges(reg)
	logger := slog.New(slog.NewTextHandler(os.Stdout, nil))

	scraper := NewScraper(mock, gauges, time.Second, logger)
	if scraper == nil {
		t.Error("NewScraper returned nil")
	}
}

// TestScraper_ContextCancellation covers the ctx.Done() branch in Run().
func TestScraper_ContextCancellation(t *testing.T) {
	mock := &testMockCollector{
		metrics: SystemMetrics{CPUPercent: 42.0, MemoryPercent: 55.0, DiskPercent: 70.0},
	}

	reg := prometheus.NewRegistry()
	gauges, err := NewGauges(reg)
	if err != nil {
		t.Fatalf("NewGauges: %v", err)
	}

	logger := slog.New(slog.NewTextHandler(os.Stdout, nil))
	scraper := NewScraper(mock, gauges, 10*time.Millisecond, logger)

	ctx, cancel := context.WithCancel(context.Background())

	done := make(chan struct{})
	go func() {
		scraper.Run(ctx)
		close(done)
	}()

	time.Sleep(50 * time.Millisecond)
	cancel()

	select {
	case <-done:
	case <-time.After(1 * time.Second):
		t.Error("scraper did not stop after context cancellation")
	}
}

// TestScraper_ContinuesAfterCollectorError covers the error log branch in scrapeOnce().
func TestScraper_ContinuesAfterCollectorError(t *testing.T) {
	mock := &testMockCollector{
		err: errors.New("collection error"),
	}

	reg := prometheus.NewRegistry()
	gauges, err := NewGauges(reg)
	if err != nil {
		t.Fatalf("NewGauges: %v", err)
	}

	logger := slog.New(slog.NewTextHandler(os.Stdout, nil))
	scraper := NewScraper(mock, gauges, 30*time.Millisecond, logger)

	ctx, cancel := context.WithTimeout(context.Background(), 150*time.Millisecond)
	defer cancel()

	scraper.Run(ctx)

	if mock.calls < 2 {
		t.Errorf("expected at least 2 calls, got %d", mock.calls)
	}
}

// TestScraper_UpdateMetrics covers the gauges.Update + debug log branch in scrapeOnce().
func TestScraper_UpdateMetrics(t *testing.T) {
	mock := &testMockCollector{
		metrics: SystemMetrics{CPUPercent: 42.0, MemoryPercent: 55.0, DiskPercent: 70.0},
	}

	reg := prometheus.NewRegistry()
	gauges, err := NewGauges(reg)
	if err != nil {
		t.Fatalf("NewGauges: %v", err)
	}

	logger := slog.New(slog.NewTextHandler(os.Stdout, &slog.HandlerOptions{Level: slog.LevelDebug}))
	scraper := NewScraper(mock, gauges, 20*time.Millisecond, logger)

	ctx, cancel := context.WithTimeout(context.Background(), 100*time.Millisecond)
	defer cancel()

	scraper.Run(ctx)

	if mock.calls == 0 {
		t.Error("expected at least one collection call")
	}

	mfs, err := reg.Gather()
	if err != nil {
		t.Fatalf("gather failed: %v", err)
	}

	foundCPU := false
	for _, mf := range mfs {
		if mf.GetName() == "server_agent_cpu_usage_percent" {
			foundCPU = true
			if len(mf.GetMetric()) > 0 {
				val := mf.GetMetric()[0].GetGauge().GetValue()
				if val != 42.0 {
					t.Errorf("expected CPU 42.0, got %f", val)
				}
			}
		}
	}

	if !foundCPU {
		t.Error("CPU metric not found in registry")
	}
}

// TestScraper_RunWithTicker verifies multiple ticks occur within the window.
func TestScraper_RunWithTicker(t *testing.T) {
	mock := &testMockCollector{
		metrics: SystemMetrics{CPUPercent: 42.0, MemoryPercent: 55.0, DiskPercent: 70.0},
	}

	reg := prometheus.NewRegistry()
	gauges, err := NewGauges(reg)
	if err != nil {
		t.Fatalf("NewGauges: %v", err)
	}

	logger := slog.New(slog.NewTextHandler(os.Stdout, nil))
	scraper := NewScraper(mock, gauges, 25*time.Millisecond, logger)

	ctx, cancel := context.WithTimeout(context.Background(), 100*time.Millisecond)
	defer cancel()

	scraper.Run(ctx)

	if mock.calls < 2 {
		t.Errorf("expected at least 2 calls with 25ms interval over 100ms, got %d", mock.calls)
	}
}

// TestScraper_ScrapeOnce_DirectCall exercises scrapeOnce directly on the success path.
func TestScraper_ScrapeOnce_DirectCall(t *testing.T) {
	mock := &testMockCollector{
		metrics: SystemMetrics{CPUPercent: 10.0, MemoryPercent: 20.0, DiskPercent: 30.0},
	}

	reg := prometheus.NewRegistry()
	gauges, err := NewGauges(reg)
	if err != nil {
		t.Fatalf("NewGauges: %v", err)
	}

	logger := slog.New(slog.NewTextHandler(os.Stdout, &slog.HandlerOptions{Level: slog.LevelDebug}))
	scraper := NewScraper(mock, gauges, time.Second, logger)

	scraper.scrapeOnce(context.Background())

	if mock.calls != 1 {
		t.Errorf("expected 1 call, got %d", mock.calls)
	}
}

// TestScraper_ScrapeOnce_ErrorPath exercises the error log branch in scrapeOnce directly.
func TestScraper_ScrapeOnce_ErrorPath(t *testing.T) {
	mock := &testMockCollector{err: errors.New("fail")}

	reg := prometheus.NewRegistry()
	gauges, err := NewGauges(reg)
	if err != nil {
		t.Fatalf("NewGauges: %v", err)
	}

	logger := slog.New(slog.NewTextHandler(os.Stdout, nil))
	scraper := NewScraper(mock, gauges, time.Second, logger)

	scraper.scrapeOnce(context.Background())

	if mock.calls != 1 {
		t.Errorf("expected 1 call, got %d", mock.calls)
	}
}