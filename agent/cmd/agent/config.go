package main

import (
	"fmt"
	"os"
	"strconv"
	"time"
)

// Config holds all runtime settings for the agent.
// Values come from environment variables so the binary stays config-free.
type Config struct {
	ListenAddr      string
	ScrapeInterval  time.Duration
	DiskPath        string
	LogLevel        string
}

// loadConfig reads environment variables and returns a Config.
// Missing variables fall back to safe defaults.
func loadConfig() (Config, error) {
	interval, err := parseDuration(
		getEnv("SCRAPE_INTERVAL", "15s"),
	)
	if err != nil {
		return Config{}, fmt.Errorf("SCRAPE_INTERVAL: %w", err)
	}

	return Config{
		ListenAddr:     getEnv("LISTEN_ADDR", ":9100"),
		ScrapeInterval: interval,
		DiskPath:       getEnv("DISK_PATH", "/"),
		LogLevel:       getEnv("LOG_LEVEL", "info"),
	}, nil
}

func getEnv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func parseDuration(s string) (time.Duration, error) {
	// Accept plain seconds as a convenience (e.g. "30").
	if sec, err := strconv.Atoi(s); err == nil {
		return time.Duration(sec) * time.Second, nil
	}
	return time.ParseDuration(s)
}
