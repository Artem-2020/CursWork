package collector

import (
    "testing"
    
    "github.com/prometheus/client_golang/prometheus"
)

func TestNewGauges_Success(t *testing.T) {
    reg := prometheus.NewRegistry()
    
    gauges, err := NewGauges(reg)
    if err != nil {
        t.Fatalf("NewGauges failed: %v", err)
    }
    
    if gauges == nil {
        t.Error("gauges is nil")
    }
}

func TestNewGauges_RegisterError(t *testing.T) {
    reg := prometheus.NewRegistry()
    
    _, err := NewGauges(reg)
    if err != nil {
        t.Fatalf("first NewGauges failed: %v", err)
    }
    
    _, err = NewGauges(reg)
    if err == nil {
        t.Error("expected error on duplicate registration, got nil")
    }
}

func TestGauges_Update(t *testing.T) {
    reg := prometheus.NewRegistry()
    
    gauges, err := NewGauges(reg)
    if err != nil {
        t.Fatalf("NewGauges failed: %v", err)
    }
    
    metrics := SystemMetrics{
        CPUPercent:    25.5,
        MemoryPercent: 60.0,
        DiskPercent:   75.5,
    }
    
    gauges.Update(metrics)
    
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
                if val != 25.5 {
                    t.Errorf("expected CPU 25.5, got %v", val)
                }
            }
        }
    }
    
    if !foundCPU {
        t.Error("CPU metric not found in registry")
    }
}


func TestGauges_UpdatePartial(t *testing.T) {
    reg := prometheus.NewRegistry()
    
    gauges, err := NewGauges(reg)
    if err != nil {
        t.Fatalf("NewGauges failed: %v", err)
    }
    
    metrics := SystemMetrics{
        CPUPercent:    25.5,
        MemoryPercent: 60.0,
        DiskPercent:   0,
    }
    
    gauges.Update(metrics)
    
    mfs, err := reg.Gather()
    if err != nil {
        t.Fatalf("gather failed: %v", err)
    }
    
    for _, mf := range mfs {
        if mf.GetName() == "server_agent_disk_usage_percent" {
            if len(mf.GetMetric()) > 0 {
                val := mf.GetMetric()[0].GetGauge().GetValue()
                if val != 0 {
                    t.Errorf("expected disk 0, got %f", val)
                }
            }
        }
    }
}

func TestNewGauges_AlreadyRegistered(t *testing.T) {
    reg := prometheus.NewRegistry()
    
    _, err := NewGauges(reg)
    if err != nil {
        t.Fatalf("first registration failed: %v", err)
    }
    
    _, err = NewGauges(reg)
    if err == nil {
        t.Error("expected error on duplicate registration, got nil")
    }
}