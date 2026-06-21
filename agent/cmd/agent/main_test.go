package main

import (
	"context"
	"log/slog"
	"os"
	"testing"
	"time"
	"syscall"
	"strings"
)

func TestBuildLogger(t *testing.T) {
	logger := buildLogger("debug")
	if logger == nil {
		t.Error("buildLogger returned nil for valid level")
	}
	logger = buildLogger("invalid")
	if logger == nil {
		t.Error("buildLogger returned nil for invalid level")
	}
}

func TestBuildLoggerWithEmptyLevel(t *testing.T) {
	logger := buildLogger("")
	if logger == nil {
		t.Error("buildLogger returned nil for empty level")
	}
}

func TestBuildLogger_InvalidLevel(t *testing.T) {
	logger := buildLogger("invalid_level_xyz")
	if logger == nil {
		t.Error("buildLogger returned nil for invalid level")
	}
}

func TestBuildLogger_AllLevels(t *testing.T) {
	levels := []string{"debug", "info", "warn", "error"}
	for _, lvl := range levels {
		l := buildLogger(lvl)
		if l == nil {
			t.Errorf("buildLogger(%q) returned nil", lvl)
		}
	}
}

// TestRun_GracefulShutdownViaContext - now ctx is passed directly to run().
func TestRun_GracefulShutdownViaContext(t *testing.T) {
	cfg := Config{
		ListenAddr:     ":0",
		ScrapeInterval: 1 * time.Second,
		DiskPath:       "/",
		LogLevel:       "info",
	}
	logger := buildLogger("info")

	ctx, cancel := context.WithCancel(context.Background())

	done := make(chan error, 1)
	go func() {
		done <- run(ctx, cfg, logger)
	}()

	time.Sleep(150 * time.Millisecond)
	cancel()

	select {
	case err := <-done:
		if err != nil && err.Error() != "http: Server closed" {
			t.Logf("run returned: %v", err)
		}
	case <-time.After(3 * time.Second):
		t.Error("run() did not return after context cancellation")
	}
}

// TestRun_InvalidListenAddr - covers the error return path from ListenAndServe.
func TestRun_InvalidListenAddr(t *testing.T) {
	cfg := Config{
		ListenAddr:     ":99999",
		ScrapeInterval: 50 * time.Millisecond,
		DiskPath:       "/",
		LogLevel:       "info",
	}
	logger := buildLogger("info")
	ctx := context.Background()

	done := make(chan error, 1)
	go func() {
		done <- run(ctx, cfg, logger)
	}()

	select {
	case err := <-done:
		if err == nil {
			t.Error("expected error for invalid listen addr, got nil")
		}
	case <-time.After(2 * time.Second):
		t.Error("run() did not return an error for invalid port")
	}
}

func TestRun_WithDebugLogLevel(t *testing.T) {
	cfg := Config{
		ListenAddr:     ":0",
		ScrapeInterval: 50 * time.Millisecond,
		DiskPath:       "/",
		LogLevel:       "debug",
	}
	logger := buildLogger("debug")
	ctx, cancel := context.WithTimeout(context.Background(), 200*time.Millisecond)
	defer cancel()

	done := make(chan error, 1)
	go func() { done <- run(ctx, cfg, logger) }()

	select {
	case err := <-done:
		if err != nil && err.Error() != "http: Server closed" {
			t.Logf("run returned: %v", err)
		}
	case <-time.After(1 * time.Second):
	}
}

func TestRun_WithErrorLogLevel(t *testing.T) {
	cfg := Config{
		ListenAddr:     ":0",
		ScrapeInterval: 50 * time.Millisecond,
		DiskPath:       "/",
		LogLevel:       "error",
	}
	logger := slog.New(slog.NewJSONHandler(os.Stdout, nil))
	ctx, cancel := context.WithTimeout(context.Background(), 200*time.Millisecond)
	defer cancel()

	done := make(chan error, 1)
	go func() { done <- run(ctx, cfg, logger) }()

	select {
	case err := <-done:
		if err != nil && err.Error() != "http: Server closed" {
			t.Logf("run returned: %v", err)
		}
	case <-time.After(1 * time.Second):
	}
}

func TestRunWithCancel(t *testing.T) {
	cfg := Config{
		ListenAddr:     ":0",
		ScrapeInterval: 1 * time.Second,
		DiskPath:       "/",
		LogLevel:       "info",
	}
	logger := buildLogger("info")
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


func TestMainFunction(t *testing.T) {

    oldArgs := os.Args
    oldEnv := os.Environ()
    defer func() {
        os.Args = oldArgs

        for _, env := range oldEnv {
            parts := strings.SplitN(env, "=", 2)
            if len(parts) == 2 {
                os.Setenv(parts[0], parts[1])
            }
        }
    }()

 
    os.Setenv("LISTEN_ADDR", ":0")
    os.Setenv("SCRAPE_INTERVAL", "1s")
    os.Setenv("DISK_PATH", "/")
    os.Setenv("LOG_LEVEL", "info")


    done := make(chan struct{})
    go func() {
      
        defer func() {
            if r := recover(); r != nil {
                t.Errorf("main panicked: %v", r)
            }
            close(done)
        }()
        main()
    }()

 
    time.Sleep(100 * time.Millisecond)

 
    p, err := os.FindProcess(os.Getpid())
    if err == nil {
        p.Signal(syscall.SIGINT)
    }

    select {
    case <-done:
  
    case <-time.After(2 * time.Second):
        t.Log("main did not exit within timeout (may still be running)")
    }
}


func TestBuildLogger_AllLevelsLowerCase(t *testing.T) {
    levels := []string{"debug", "info", "warn", "error"}
    for _, lvl := range levels {
        logger := buildLogger(lvl)
        if logger == nil {
            t.Errorf("buildLogger(%q) returned nil", lvl)
        }
    }
}


func TestBuildLogger_AllLevelsUpperCase(t *testing.T) {
    levels := []string{"DEBUG", "INFO", "WARN", "ERROR"}
    for _, lvl := range levels {
        logger := buildLogger(lvl)
        if logger == nil {
            t.Errorf("buildLogger(%q) returned nil", lvl)
        }
    }
}


func TestBuildLogger_LogOutput(t *testing.T) {
    logger := buildLogger("info")
    if logger == nil {
        t.Fatal("buildLogger returned nil")
    }
    logger.Info("test message")
}

