package collector

import "github.com/prometheus/client_golang/prometheus"

const namespace = "server_agent"

// Gauges holds the three Prometheus gauges exposed by this agent.
// Each gauge is a separate metric that Prometheus scrapes over time.
type Gauges struct {
	cpu    prometheus.Gauge
	memory prometheus.Gauge
	disk   prometheus.Gauge
}

// NewGauges creates and registers the three gauges with the given registerer.
// Pass prometheus.DefaultRegisterer in production; pass a test registry in tests.
func NewGauges(reg prometheus.Registerer) (*Gauges, error) {
	g := &Gauges{
		cpu: prometheus.NewGauge(prometheus.GaugeOpts{
			Namespace: namespace,
			Name:      "cpu_usage_percent",
			Help:      "Current CPU utilisation across all cores (0–100).",
		}),
		memory: prometheus.NewGauge(prometheus.GaugeOpts{
			Namespace: namespace,
			Name:      "memory_usage_percent",
			Help:      "Current RAM utilisation (0–100).",
		}),
		disk: prometheus.NewGauge(prometheus.GaugeOpts{
			Namespace: namespace,
			Name:      "disk_usage_percent",
			Help:      "Current disk utilisation for the monitored path (0–100).",
		}),
	}

	for _, gauge := range []prometheus.Collector{g.cpu, g.memory, g.disk} {
		if err := reg.Register(gauge); err != nil {
			return nil, err
		}
	}

	return g, nil
}

// Update pushes fresh metric values into the gauges.
func (g *Gauges) Update(m SystemMetrics) {
	g.cpu.Set(m.CPUPercent)
	g.memory.Set(m.MemoryPercent)
	g.disk.Set(m.DiskPercent)
}
