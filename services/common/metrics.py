import logging

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Simple metrics collector for services"""

    def __init__(self, service_name: str):
        self.service_name = service_name
        self._counters: dict[str, int] = {}
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, list] = {}

    def increment_counter(self, name: str, labels: dict[str, str] = None, value: int = 1):
        """Increment a counter metric"""
        key = self._make_key(name, labels)
        self._counters[key] = self._counters.get(key, 0) + value

    def set_gauge(self, name: str, value: float, labels: dict[str, str] = None):
        """Set a gauge metric"""
        key = self._make_key(name, labels)
        self._gauges[key] = value

    def observe_histogram(self, name: str, value: float, labels: dict[str, str] = None):
        """Observe a value in histogram"""
        key = self._make_key(name, labels)
        if key not in self._histograms:
            self._histograms[key] = []
        self._histograms[key].append(value)

    def _make_key(self, name: str, labels: dict[str, str] = None) -> str:
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    def get_metrics(self) -> str:
        """Get all metrics in Prometheus format"""
        lines = []

        for name, value in self._counters.items():
            lines.append(f"# TYPE {self.service_name}_{name} counter")
            lines.append(f"{self.service_name}_{name} {value}")

        for name, value in self._gauges.items():
            lines.append(f"# TYPE {self.service_name}_{name} gauge")
            lines.append(f"{self.service_name}_{name} {value}")

        for name, values in self._histograms.items():
            if values:
                avg = sum(values) / len(values)
                lines.append(f"# TYPE {self.service_name}_{name} histogram")
                lines.append(f"{self.service_name}_{name}_sum {sum(values)}")
                lines.append(f"{self.service_name}_{name}_count {len(values)}")
                lines.append(f"{self.service_name}_{name}_avg {avg}")

        return "\n".join(lines)

    def reset(self):
        """Reset all metrics"""
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()


_metrics_collector = None


def get_metrics_collector(service_name: str = "app") -> MetricsCollector:
    """Get or create metrics collector"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector(service_name)
    return _metrics_collector


def track_task_processed(task_type: str, status: str):
    """Track a processed task"""
    collector = get_metrics_collector()
    collector.increment_counter(
        "tasks_processed_total", labels={"task_type": task_type, "status": status}
    )


def track_task_duration(task_type: str, duration: float):
    """Track task processing duration"""
    collector = get_metrics_collector()
    collector.observe_histogram("task_duration_seconds", duration, labels={"task_type": task_type})


def track_error(error_type: str):
    """Track an error"""
    collector = get_metrics_collector()
    collector.increment_counter("errors_total", labels={"error_type": error_type})


def set_queue_size(size: int):
    """Set current queue size"""
    collector = get_metrics_collector()
    collector.set_gauge("queue_size", float(size))


def set_active_workers(count: int):
    """Set number of active workers"""
    collector = get_metrics_collector()
    collector.set_gauge("active_workers", float(count))
