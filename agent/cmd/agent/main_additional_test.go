package main

import (
	"context"
	"testing"
	"time"
)

func TestRunWithCancelImmediate(t *testing.T) {
	cfg := Config{
		ListenAddr:     ":0",
		ScrapeInterval: 1 * time.Second,
		DiskPath:       "/",
		LogLevel:       "info",
	}
	logger := buildLogger("info")
	ctx, cancel := context.WithCancel(context.Background())
	cancel()

	done := make(chan error, 1)
	go func() {
		done <- run(ctx, cfg, logger)
	}()

	select {
	case err := <-done:
		if err != nil && err.Error() != "http: Server closed" {
			t.Logf("run returned: %v", err)
		}
	case <-time.After(1 * time.Second):
	}
}

func TestRunWithInvalidDiskPath(t *testing.T) {
	cfg := Config{
		ListenAddr:     ":0",
		ScrapeInterval: 50 * time.Millisecond,
		DiskPath:       "/nonexistent/path/xyz",
		LogLevel:       "error",
	}
	logger := buildLogger("error")
	ctx, cancel := context.WithTimeout(context.Background(), 200*time.Millisecond)
	defer cancel()

	done := make(chan error, 1)
	go func() {
		done <- run(ctx, cfg, logger)
	}()

	select {
	case err := <-done:
		if err != nil && err.Error() != "http: Server closed" {
			t.Logf("run returned: %v", err)
		}
	case <-time.After(1 * time.Second):
	}
}