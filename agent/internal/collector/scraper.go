package collector

import (
	"context"
	"log/slog"
	"time"
)

// Scraper runs a polling loop: every interval it calls the Collector,
// then hands the result to the Gauges for Prometheus to read.
type Scraper struct {
	collector Collector
	gauges    *Gauges
	interval  time.Duration
	logger    *slog.Logger
}

// NewScraper wires up the scrape loop dependencies.
func NewScraper(c Collector, g *Gauges, interval time.Duration, logger *slog.Logger) *Scraper {
	return &Scraper{
		collector: c,
		gauges:    g,
		interval:  interval,
		logger:    logger,
	}
}

// Run blocks until ctx is cancelled, collecting metrics on every tick.
// Call it in its own goroutine.
func (s *Scraper) Run(ctx context.Context) {
	ticker := time.NewTicker(s.interval)
	defer ticker.Stop()

	s.logger.Info("scraper started", "interval", s.interval)

	for {
		select {
		case <-ctx.Done():
			s.logger.Info("scraper stopped")
			return
		case <-ticker.C:
			s.scrapeOnce(ctx)
		}
	}
}

func (s *Scraper) scrapeOnce(ctx context.Context) {
	metrics, err := s.collector.Collect(ctx)
	if err != nil {
		// Log and continue — a single failed scrape is not fatal.
		s.logger.Error("failed to collect metrics", "err", err)
		return
	}
	s.gauges.Update(metrics)
	s.logger.Debug("metrics updated",
		"cpu", metrics.CPUPercent,
		"memory", metrics.MemoryPercent,
		"disk", metrics.DiskPercent,
	)
}
