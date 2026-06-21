package collector

import (
	"testing"
)

// TestCollectorInterface verifies SystemCollector implements the Collector interface.
func TestCollectorInterface(t *testing.T) {
	var _ Collector = (*SystemCollector)(nil)
}

func TestSystemMetrics_Values(t *testing.T) {
	m := SystemMetrics{
		CPUPercent:    10.5,
		MemoryPercent: 20.5,
		DiskPercent:   30.5,
	}
	if m.CPUPercent != 10.5 {
		t.Errorf("expected CPUPercent 10.5, got %f", m.CPUPercent)
	}
	if m.MemoryPercent != 20.5 {
		t.Errorf("expected MemoryPercent 20.5, got %f", m.MemoryPercent)
	}
	if m.DiskPercent != 30.5 {
		t.Errorf("expected DiskPercent 30.5, got %f", m.DiskPercent)
	}
}