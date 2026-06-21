package collector

import (
	"context"
	"fmt"

	"github.com/shirou/gopsutil/v3/cpu"
	"github.com/shirou/gopsutil/v3/disk"
	"github.com/shirou/gopsutil/v3/mem"
)

// osReader groups the OS-level calls that SystemCollector depends on.
// In production the real gopsutil functions are used; in tests they can be replaced.
type osReader struct {
	cpuPercent    func(ctx context.Context, interval float64, percpu bool) ([]float64, error)
	virtualMemory func() (*mem.VirtualMemoryStat, error)
	diskUsage     func(path string) (*disk.UsageStat, error)
}

var defaultOSReader = osReader{
	cpuPercent: func(ctx context.Context, interval float64, percpu bool) ([]float64, error) {
		return cpu.PercentWithContext(ctx, 0, percpu)
	},
	virtualMemory: mem.VirtualMemory,
	diskUsage:     disk.Usage,
}

// SystemCollector reads metrics from the host OS via gopsutil.
// It implements the Collector interface.
type SystemCollector struct {
	diskPath string
	os       osReader
}

// NewSystemCollector creates a collector that watches the given disk path.
// Passing "/" covers the root filesystem on Linux.
func NewSystemCollector(diskPath string) *SystemCollector {
	return &SystemCollector{diskPath: diskPath, os: defaultOSReader}
}

// Collect reads CPU, memory, and disk usage in a single call.
// It returns an error if any individual reading fails.
func (c *SystemCollector) Collect(ctx context.Context) (SystemMetrics, error) {
	cpuPercent, err := c.readCPU(ctx)
	if err != nil {
		return SystemMetrics{}, fmt.Errorf("read cpu: %w", err)
	}

	memPercent, err := c.readMemory()
	if err != nil {
		return SystemMetrics{}, fmt.Errorf("read memory: %w", err)
	}

	diskPercent, err := c.readDisk()
	if err != nil {
		return SystemMetrics{}, fmt.Errorf("read disk: %w", err)
	}

	return SystemMetrics{
		CPUPercent:    cpuPercent,
		MemoryPercent: memPercent,
		DiskPercent:   diskPercent,
	}, nil
}

func (c *SystemCollector) readCPU(ctx context.Context) (float64, error) {
	// percpu=false -> single aggregate value across all cores.
	percents, err := c.os.cpuPercent(ctx, 0, false)
	if err != nil {
		return 0, err
	}
	if len(percents) == 0 {
		return 0, fmt.Errorf("no cpu data returned")
	}
	return percents[0], nil
}

func (c *SystemCollector) readMemory() (float64, error) {
	stat, err := c.os.virtualMemory()
	if err != nil {
		return 0, err
	}
	return stat.UsedPercent, nil
}

func (c *SystemCollector) readDisk() (float64, error) {
	stat, err := c.os.diskUsage(c.diskPath)
	if err != nil {
		return 0, err
	}
	return stat.UsedPercent, nil
}