package main

import (
	"context"
	"log/slog"
	"os"
	"os/signal"
	"syscall"

	"github.com/prometheus/client_golang/prometheus"

	"github.com/yourname/server-agent/internal/collector"
	"github.com/yourname/server-agent/internal/server"
)

func main() {
	cfg, err := loadConfig()
	if err != nil {
		slog.Error("invalid config", "err", err)
		os.Exit(1)
	}

	logger := buildLogger(cfg.LogLevel)

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	if err := run(ctx, cfg, logger); err != nil {
		logger.Error("agent exited with error", "err", err)
		os.Exit(1)
	}
}

func run(ctx context.Context, cfg Config, logger *slog.Logger) error {
	reg := prometheus.NewRegistry()

	gauges, err := collector.NewGauges(reg)
	if err != nil {
		return err
	}

	sys := collector.NewSystemCollector(cfg.DiskPath)
	scraper := collector.NewScraper(sys, gauges, cfg.ScrapeInterval, logger)
	srv := server.New(cfg.ListenAddr, reg, logger)

	go scraper.Run(ctx)

	return srv.ListenAndServe(ctx)
}

func buildLogger(level string) *slog.Logger {
	var l slog.Level
	if err := l.UnmarshalText([]byte(level)); err != nil {
		l = slog.LevelInfo
	}
	return slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{Level: l}))
}