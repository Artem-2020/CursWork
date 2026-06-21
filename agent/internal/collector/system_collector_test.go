package collector

import (
	"context"
	"errors"
	"testing"

	"github.com/shirou/gopsutil/v3/disk"
	"github.com/shirou/gopsutil/v3/mem"
)

// newCollectorWithReader creates a SystemCollector with injected OS functions for testing.
func newCollectorWithReader(diskPath string, r osReader) *SystemCollector {
	return &SystemCollector{diskPath: diskPath, os: r}
}

func okReader() osReader {
	return osReader{
		cpuPercent: func(_ context.Context, _ float64, _ bool) ([]float64, error) {
			return []float64{42.0}, nil
		},
		virtualMemory: func() (*mem.VirtualMemoryStat, error) {
			return &mem.VirtualMemoryStat{UsedPercent: 55.0}, nil
		},
		diskUsage: func(_ string) (*disk.UsageStat, error) {
			return &disk.UsageStat{UsedPercent: 70.0}, nil
		},
	}
}

// --- Collect happy path (mock) ---

func TestSystemCollector_Collect_HappyPath(t *testing.T) {
	c := newCollectorWithReader("/", okReader())
	m, err := c.Collect(context.Background())
	if err != nil {
		t.Fatalf("Collect failed: %v", err)
	}
	if m.CPUPercent != 42.0 {
		t.Errorf("expected CPU 42.0, got %f", m.CPUPercent)
	}
	if m.MemoryPercent != 55.0 {
		t.Errorf("expected Memory 55.0, got %f", m.MemoryPercent)
	}
	if m.DiskPercent != 70.0 {
		t.Errorf("expected Disk 70.0, got %f", m.DiskPercent)
	}
}

// --- Collect integration (real OS) ---

func TestSystemCollector_Collect(t *testing.T) {
	c := NewSystemCollector("/")
	metrics, err := c.Collect(context.Background())
	if err != nil {
		t.Fatalf("Collect failed: %v", err)
	}
	if metrics.CPUPercent < 0 || metrics.CPUPercent > 100 {
		t.Errorf("CPUPercent out of range: %f", metrics.CPUPercent)
	}
	if metrics.MemoryPercent < 0 || metrics.MemoryPercent > 100 {
		t.Errorf("MemoryPercent out of range: %f", metrics.MemoryPercent)
	}
	if metrics.DiskPercent < 0 || metrics.DiskPercent > 100 {
		t.Errorf("DiskPercent out of range: %f", metrics.DiskPercent)
	}
}

// --- readCPU ---

func TestSystemCollector_ReadCPU(t *testing.T) {
	c := NewSystemCollector("/")
	v, err := c.readCPU(context.Background())
	if err != nil {
		t.Fatalf("readCPU failed: %v", err)
	}
	if v < 0 || v > 100 {
		t.Errorf("CPU out of range: %f", v)
	}
}

func TestSystemCollector_ReadCPU_Error(t *testing.T) {
	r := okReader()
	r.cpuPercent = func(_ context.Context, _ float64, _ bool) ([]float64, error) {
		return nil, errors.New("cpu error")
	}
	c := newCollectorWithReader("/", r)
	_, err := c.readCPU(context.Background())
	if err == nil {
		t.Error("expected error from readCPU, got nil")
	}
}

func TestSystemCollector_ReadCPU_EmptySlice(t *testing.T) {
	r := okReader()
	r.cpuPercent = func(_ context.Context, _ float64, _ bool) ([]float64, error) {
		return []float64{}, nil
	}
	c := newCollectorWithReader("/", r)
	_, err := c.readCPU(context.Background())
	if err == nil {
		t.Error("expected error for empty cpu slice, got nil")
	}
}

func TestSystemCollector_ReadCPU_WithContext(t *testing.T) {
	c := NewSystemCollector("/")
	v, err := c.readCPU(context.Background())
	if err != nil {
		t.Logf("readCPU error: %v", err)
	}
	if v < 0 || v > 100 {
		t.Errorf("CPU out of range: %f", v)
	}
}

// --- readMemory ---

func TestSystemCollector_ReadMemory(t *testing.T) {
	c := NewSystemCollector("/")
	v, err := c.readMemory()
	if err != nil {
		t.Fatalf("readMemory failed: %v", err)
	}
	if v < 0 || v > 100 {
		t.Errorf("Memory out of range: %f", v)
	}
}

func TestSystemCollector_ReadMemory_Error(t *testing.T) {
	r := okReader()
	r.virtualMemory = func() (*mem.VirtualMemoryStat, error) {
		return nil, errors.New("mem error")
	}
	c := newCollectorWithReader("/", r)
	_, err := c.readMemory()
	if err == nil {
		t.Error("expected error from readMemory, got nil")
	}
}

// --- readDisk ---

func TestSystemCollector_ReadDisk(t *testing.T) {
	c := NewSystemCollector("/")
	v, err := c.readDisk()
	if err != nil {
		t.Fatalf("readDisk failed: %v", err)
	}
	if v < 0 || v > 100 {
		t.Errorf("Disk out of range: %f", v)
	}
}

func TestSystemCollector_ReadDisk_Error(t *testing.T) {
	r := okReader()
	r.diskUsage = func(_ string) (*disk.UsageStat, error) {
		return nil, errors.New("disk error")
	}
	c := newCollectorWithReader("/", r)
	_, err := c.readDisk()
	if err == nil {
		t.Error("expected error from readDisk, got nil")
	}
}

// --- Collect error propagation ---

func TestSystemCollector_Collect_CPUError(t *testing.T) {
	r := okReader()
	r.cpuPercent = func(_ context.Context, _ float64, _ bool) ([]float64, error) {
		return nil, errors.New("cpu fail")
	}
	c := newCollectorWithReader("/", r)
	_, err := c.Collect(context.Background())
	if err == nil {
		t.Error("expected error when CPU fails")
	}
}

func TestSystemCollector_Collect_MemoryError(t *testing.T) {
	r := okReader()
	r.virtualMemory = func() (*mem.VirtualMemoryStat, error) {
		return nil, errors.New("mem fail")
	}
	c := newCollectorWithReader("/", r)
	_, err := c.Collect(context.Background())
	if err == nil {
		t.Error("expected error when memory fails")
	}
}

func TestSystemCollector_Collect_DiskError(t *testing.T) {
	r := okReader()
	r.diskUsage = func(_ string) (*disk.UsageStat, error) {
		return nil, errors.New("disk fail")
	}
	c := newCollectorWithReader("/", r)
	_, err := c.Collect(context.Background())
	if err == nil {
		t.Error("expected error when disk fails")
	}
}

func TestSystemCollector_Collect_WithContextCancellation(t *testing.T) {
	c := NewSystemCollector("/")
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	_, err := c.Collect(ctx)
	_ = err
}