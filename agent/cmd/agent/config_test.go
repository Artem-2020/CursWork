package main

import (
    "os"
    "testing"
    "time"
)

func TestLoadConfigDefaults(t *testing.T) {
    cfg, err := loadConfig()
    if err != nil {
        t.Fatalf("loadConfig failed: %v", err)
    }
    
    if cfg.ListenAddr != ":9100" {
        t.Errorf("expected :9100, got %s", cfg.ListenAddr)
    }
    if cfg.ScrapeInterval != 15*time.Second {
        t.Errorf("expected 15s, got %v", cfg.ScrapeInterval)
    }
    if cfg.DiskPath != "/" {
        t.Errorf("expected /, got %s", cfg.DiskPath)
    }
    if cfg.LogLevel != "info" {
        t.Errorf("expected info, got %s", cfg.LogLevel)
    }
}

func TestLoadConfigWithEnv(t *testing.T) {
    os.Setenv("LISTEN_ADDR", ":8080")
    os.Setenv("SCRAPE_INTERVAL", "30s")
    defer func() {
        os.Unsetenv("LISTEN_ADDR")
        os.Unsetenv("SCRAPE_INTERVAL")
    }()
    
    cfg, err := loadConfig()
    if err != nil {
        t.Fatalf("loadConfig failed: %v", err)
    }
    
    if cfg.ListenAddr != ":8080" {
        t.Errorf("expected :8080, got %s", cfg.ListenAddr)
    }
    if cfg.ScrapeInterval != 30*time.Second {
        t.Errorf("expected 30s, got %v", cfg.ScrapeInterval)
    }
}

func TestParseDuration(t *testing.T) {
    d, err := parseDuration("30")
    if err != nil || d != 30*time.Second {
        t.Errorf("parseDuration('30') = %v, want 30s", d)
    }
    
    d, err = parseDuration("1m30s")
    if err != nil || d != 90*time.Second {
        t.Errorf("parseDuration('1m30s') = %v, want 90s", d)
    }
}

func TestParseDurationInvalid(t *testing.T) {
    _, err := parseDuration("invalid")
    if err == nil {
        t.Error("expected error for invalid duration, got nil")
    }
}

func TestGetEnvFallback(t *testing.T) {
    if got := getEnv("NON_EXISTENT_VAR", "default"); got != "default" {
        t.Errorf("expected default, got %s", got)
    }
    
    os.Setenv("TEST_VAR", "value")
    if got := getEnv("TEST_VAR", "default"); got != "value" {
        t.Errorf("expected value, got %s", got)
    }
    os.Unsetenv("TEST_VAR")
}

func TestLoadConfigWithAllEnvVars(t *testing.T) {
    os.Setenv("LISTEN_ADDR", ":9090")
    os.Setenv("SCRAPE_INTERVAL", "10s")
    os.Setenv("DISK_PATH", "/home")
    os.Setenv("LOG_LEVEL", "debug")
    
    defer func() {
        os.Unsetenv("LISTEN_ADDR")
        os.Unsetenv("SCRAPE_INTERVAL")
        os.Unsetenv("DISK_PATH")
        os.Unsetenv("LOG_LEVEL")
    }()
    
    cfg, err := loadConfig()
    if err != nil {
        t.Fatalf("loadConfig failed: %v", err)
    }
    
    if cfg.ListenAddr != ":9090" {
        t.Errorf("expected :9090, got %s", cfg.ListenAddr)
    }
    if cfg.ScrapeInterval != 10*time.Second {
        t.Errorf("expected 10s, got %v", cfg.ScrapeInterval)
    }
    if cfg.DiskPath != "/home" {
        t.Errorf("expected /home, got %s", cfg.DiskPath)
    }
    if cfg.LogLevel != "debug" {
        t.Errorf("expected debug, got %s", cfg.LogLevel)
    }
}

func TestParseDurationSecondsAsNumber(t *testing.T) {
    d, err := parseDuration("45")
    if err != nil {
        t.Fatalf("parseDuration failed: %v", err)
    }
    if d != 45*time.Second {
        t.Errorf("expected 45s, got %v", d)
    }
}

func TestParseDurationMinutesAndSeconds(t *testing.T) {
    d, err := parseDuration("2m30s")
    if err != nil {
        t.Fatalf("parseDuration failed: %v", err)
    }
    if d != 150*time.Second {
        t.Errorf("expected 150s, got %v", d)
    }
}

func TestGetEnvExists(t *testing.T) {
    os.Setenv("TEST_GET_ENV", "exists")
    defer os.Unsetenv("TEST_GET_ENV")
    
    if got := getEnv("TEST_GET_ENV", "default"); got != "exists" {
        t.Errorf("expected 'exists', got '%s'", got)
    }
}

func TestGetEnvNotExists(t *testing.T) {
    if got := getEnv("NON_EXISTENT_VAR_12345", "fallback"); got != "fallback" {
        t.Errorf("expected 'fallback', got '%s'", got)
    }
}


func TestParseDurationMinutes(t *testing.T) {
    d, err := parseDuration("5m")
    if err != nil {
        t.Fatalf("parseDuration failed: %v", err)
    }
    if d != 5*time.Minute {
        t.Errorf("expected 5m, got %v", d)
    }
}

func TestParseDurationHours(t *testing.T) {
    d, err := parseDuration("2h")
    if err != nil {
        t.Fatalf("parseDuration failed: %v", err)
    }
    if d != 2*time.Hour {
        t.Errorf("expected 2h, got %v", d)
    }
}

func TestParseDurationCombined(t *testing.T) {
    d, err := parseDuration("1h30m")
    if err != nil {
        t.Fatalf("parseDuration failed: %v", err)
    }
    if d != 90*time.Minute {
        t.Errorf("expected 1h30m, got %v", d)
    }
}

func TestParseDurationZero(t *testing.T) {
    d, err := parseDuration("0")
    if err != nil {
        t.Fatalf("parseDuration failed: %v", err)
    }
    if d != 0 {
        t.Errorf("expected 0, got %v", d)
    }
}

func TestLoadConfig_InvalidInterval(t *testing.T) {
    os.Setenv("SCRAPE_INTERVAL", "invalid")
    defer os.Unsetenv("SCRAPE_INTERVAL")
    
    _, err := loadConfig()
    if err == nil {
        t.Error("expected error for invalid SCRAPE_INTERVAL, got nil")
    }
}

func TestParseDuration_InvalidFormat(t *testing.T) {
    _, err := parseDuration("1x2y")
    if err == nil {
        t.Error("expected error for invalid duration format, got nil")
    }
}

func TestLoadConfig_AllDefaults(t *testing.T) {
 
    os.Unsetenv("LISTEN_ADDR")
    os.Unsetenv("SCRAPE_INTERVAL")
    os.Unsetenv("DISK_PATH")
    os.Unsetenv("LOG_LEVEL")
    
    cfg, err := loadConfig()
    if err != nil {
        t.Fatalf("loadConfig failed: %v", err)
    }
    
    if cfg.ListenAddr != ":9100" {
        t.Errorf("expected :9100, got %s", cfg.ListenAddr)
    }
    if cfg.ScrapeInterval != 15*time.Second {
        t.Errorf("expected 15s, got %v", cfg.ScrapeInterval)
    }
    if cfg.DiskPath != "/" {
        t.Errorf("expected /, got %s", cfg.DiskPath)
    }
    if cfg.LogLevel != "info" {
        t.Errorf("expected info, got %s", cfg.LogLevel)
    }
}

func TestLoadConfig_InvalidIntervalAsString(t *testing.T) {
    os.Setenv("SCRAPE_INTERVAL", "not-a-number")
    defer os.Unsetenv("SCRAPE_INTERVAL")
    
    _, err := loadConfig()
    if err == nil {
        t.Error("expected error for invalid SCRAPE_INTERVAL, got nil")
    }
}

func TestLoadConfig_EmptyScrapeInterval(t *testing.T) {
    os.Setenv("SCRAPE_INTERVAL", "")
    defer os.Unsetenv("SCRAPE_INTERVAL")
    
    cfg, err := loadConfig()
    if err != nil {
        t.Fatalf("loadConfig failed: %v", err)
    }
    if cfg.ScrapeInterval != 15*time.Second {
        t.Errorf("expected default 15s, got %v", cfg.ScrapeInterval)
    }
}

func TestLoadConfig_ZeroScrapeInterval(t *testing.T) {
    os.Setenv("SCRAPE_INTERVAL", "0")
    defer os.Unsetenv("SCRAPE_INTERVAL")
    
    cfg, err := loadConfig()
    if err != nil {
        t.Fatalf("loadConfig failed: %v", err)
    }
    if cfg.ScrapeInterval != 0 {
        t.Errorf("expected 0s, got %v", cfg.ScrapeInterval)
    }
}

func TestGetEnv_WithEmptyString(t *testing.T) {
    os.Setenv("EMPTY_VAR", "")
    defer os.Unsetenv("EMPTY_VAR")

    if got := getEnv("EMPTY_VAR", "fallback"); got != "fallback" {
        t.Errorf("expected 'fallback' for empty env var, got '%s'", got)
    }
}