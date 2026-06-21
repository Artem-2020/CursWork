package collector

import (
	"testing"
)

func TestSystemMetrics_ZeroValues(t *testing.T) {
	m := SystemMetrics{}

	if m.CPUPercent != 0 {
		t.Errorf("expected CPUPercent 0, got %f", m.CPUPercent)
	}
	if m.MemoryPercent != 0 {
		t.Errorf("expected MemoryPercent 0, got %f", m.MemoryPercent)
	}
	if m.DiskPercent != 0 {
		t.Errorf("expected DiskPercent 0, got %f", m.DiskPercent)
	}
}

// TestSystemCollector_NewSystemCollector_DiskPath verifies diskPath is stored correctly.
func TestSystemCollector_NewSystemCollector_DiskPath(t *testing.T) {
	c1 := NewSystemCollector("/")
	if c1.diskPath != "/" {
		t.Errorf("expected '/', got '%s'", c1.diskPath)
	}

	c2 := NewSystemCollector("/home")
	if c2.diskPath != "/home" {
		t.Errorf("expected '/home', got '%s'", c2.diskPath)
	}
}