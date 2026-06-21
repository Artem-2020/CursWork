package collector

import "context"

// Collector describes anything that can read current system metrics.
// Using an interface here keeps the server and tests free of gopsutil.
type Collector interface {
	Collect(ctx context.Context) (SystemMetrics, error)
}
