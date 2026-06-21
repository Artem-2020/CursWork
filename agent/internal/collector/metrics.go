package collector

// SystemMetrics holds a single snapshot of server resource usage.
type SystemMetrics struct {
	CPUPercent    float64
	MemoryPercent float64
	DiskPercent   float64
}
