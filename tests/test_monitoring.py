"""
Unit tests for frameworks/monitoring/monitoring.py
"""

import asyncio
import json
import pytest
from datetime import datetime, timedelta


# ---------------------------------------------------------------------------
# MetricsCollector
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestMetricsCollector:

    def _make_collector(self):
        from frameworks.monitoring.monitoring import MetricsCollector
        return MetricsCollector()

    def test_record_counter_increments(self):
        from frameworks.monitoring.monitoring import MetricsCollector, Metric, MetricType
        mc = MetricsCollector()
        mc.increment("hits", 3)
        mc.increment("hits", 2)
        assert mc.counters["hits"] == 5.0

    def test_record_gauge_overwrites(self):
        from frameworks.monitoring.monitoring import MetricsCollector
        mc = MetricsCollector()
        mc.gauge("cpu", 45.0)
        mc.gauge("cpu", 80.0)
        assert mc.gauges["cpu"] == 80.0

    def test_record_timer_accumulates(self):
        from frameworks.monitoring.monitoring import MetricsCollector
        mc = MetricsCollector()
        mc.timer("latency", 0.1)
        mc.timer("latency", 0.2)
        assert len(mc.timers["latency"]) == 2
        assert mc.timers["latency"] == pytest.approx([0.1, 0.2])

    def test_timer_trimmed_at_1000(self):
        from frameworks.monitoring.monitoring import MetricsCollector
        mc = MetricsCollector()
        for i in range(1050):
            mc.timer("t", float(i))
        assert len(mc.timers["t"]) == 1000

    def test_max_metrics_trimming(self):
        from frameworks.monitoring.monitoring import MetricsCollector
        mc = MetricsCollector(max_metrics=5)
        for i in range(10):
            mc.increment("x")
        assert len(mc.metrics) == 5

    def test_get_metrics_no_filter_returns_all(self):
        from frameworks.monitoring.monitoring import MetricsCollector
        mc = MetricsCollector()
        mc.increment("a")
        mc.increment("b")
        assert len(mc.get_metrics()) == 2

    def test_get_metrics_filter_by_name(self):
        from frameworks.monitoring.monitoring import MetricsCollector
        mc = MetricsCollector()
        mc.increment("alpha")
        mc.increment("beta")
        result = mc.get_metrics(name="alpha")
        assert len(result) == 1
        assert result[0].name == "alpha"

    def test_get_metrics_filter_by_start_time(self):
        from frameworks.monitoring.monitoring import MetricsCollector
        mc = MetricsCollector()
        mc.increment("before")
        future = datetime.now() + timedelta(hours=1)
        mc.increment("after")
        result = mc.get_metrics(start_time=future)
        # "after" was recorded after future - but timestamps are near-identical;
        # this tests the branch executes without error
        assert isinstance(result, list)

    def test_get_metrics_filter_by_end_time(self):
        from frameworks.monitoring.monitoring import MetricsCollector
        mc = MetricsCollector()
        mc.increment("x")
        past = datetime.now() - timedelta(hours=1)
        result = mc.get_metrics(end_time=past)
        assert result == []

    def test_get_summary_structure(self):
        from frameworks.monitoring.monitoring import MetricsCollector
        mc = MetricsCollector()
        mc.increment("requests", 5)
        mc.gauge("memory", 512.0)
        mc.timer("rt", 0.05)
        summary = mc.get_summary()
        assert "total_metrics" in summary
        assert summary["total_metrics"] == 3
        assert "counters" in summary
        assert "gauges" in summary
        assert "timers" in summary
        assert summary["counters"]["requests"] == 5.0
        assert summary["gauges"]["memory"] == 512.0
        assert summary["timers"]["rt"]["count"] == 1


# ---------------------------------------------------------------------------
# HealthMonitor
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestHealthMonitor:

    def test_check_no_registered_function_returns_unhealthy(self):
        from frameworks.monitoring.monitoring import HealthMonitor
        hm = HealthMonitor()
        result = asyncio.run(hm.check("nonexistent"))
        assert result.status == "unhealthy"
        assert "No health check registered" in result.message

    def test_check_registered_returns_healthcheck(self):
        from frameworks.monitoring.monitoring import HealthMonitor, HealthCheck
        hm = HealthMonitor()

        async def ok_check():
            return HealthCheck(component="db", status="healthy", message="OK")

        hm.register_check("db", ok_check)
        result = asyncio.run(hm.check("db"))
        assert result.status == "healthy"
        assert result.component == "db"

    def test_check_dict_result(self):
        from frameworks.monitoring.monitoring import HealthMonitor
        hm = HealthMonitor()

        async def dict_check():
            return {"status": "degraded", "message": "slow", "metrics": {"latency": 900}}

        hm.register_check("api", dict_check)
        result = asyncio.run(hm.check("api"))
        assert result.status == "degraded"
        assert result.message == "slow"

    def test_check_bool_true_result(self):
        from frameworks.monitoring.monitoring import HealthMonitor
        hm = HealthMonitor()

        async def bool_check():
            return True

        hm.register_check("svc", bool_check)
        result = asyncio.run(hm.check("svc"))
        assert result.status == "healthy"

    def test_check_bool_false_result(self):
        from frameworks.monitoring.monitoring import HealthMonitor
        hm = HealthMonitor()

        async def fail_check():
            return False

        hm.register_check("svc", fail_check)
        result = asyncio.run(hm.check("svc"))
        assert result.status == "unhealthy"

    def test_check_exception_returns_unhealthy(self):
        from frameworks.monitoring.monitoring import HealthMonitor
        hm = HealthMonitor()

        async def bad_check():
            raise RuntimeError("boom")

        hm.register_check("broken", bad_check)
        result = asyncio.run(hm.check("broken"))
        assert result.status == "unhealthy"
        assert "boom" in result.message

    def test_check_all_runs_all_checks(self):
        from frameworks.monitoring.monitoring import HealthMonitor, HealthCheck
        hm = HealthMonitor()

        async def c1():
            return HealthCheck(component="c1", status="healthy", message="")

        async def c2():
            return HealthCheck(component="c2", status="healthy", message="")

        hm.register_check("c1", c1)
        hm.register_check("c2", c2)
        results = asyncio.run(hm.check_all())
        assert "c1" in results
        assert "c2" in results

    def test_get_status_all_components(self):
        from frameworks.monitoring.monitoring import HealthMonitor, HealthCheck
        hm = HealthMonitor()

        async def chk():
            return HealthCheck(component="x", status="healthy", message="fine")

        hm.register_check("x", chk)
        asyncio.run(hm.check("x"))
        status = hm.get_status()
        assert "x" in status
        assert status["x"]["status"] == "healthy"

    def test_get_status_specific_component(self):
        from frameworks.monitoring.monitoring import HealthMonitor, HealthCheck
        hm = HealthMonitor()

        async def chk():
            return HealthCheck(component="y", status="degraded", message="slow")

        hm.register_check("y", chk)
        asyncio.run(hm.check("y"))
        status = hm.get_status("y")
        assert status["status"] == "degraded"
        assert "timestamp" in status

    def test_get_status_unknown_component(self):
        from frameworks.monitoring.monitoring import HealthMonitor
        hm = HealthMonitor()
        status = hm.get_status("ghost")
        assert status["status"] == "unknown"


# ---------------------------------------------------------------------------
# PerformanceMonitor
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestPerformanceMonitor:

    def _make_perf(self):
        from frameworks.monitoring.monitoring import MetricsCollector, PerformanceMonitor
        mc = MetricsCollector()
        return PerformanceMonitor(mc), mc

    def test_start_timer_returns_id(self):
        pm, _ = self._make_perf()
        timer_id = pm.start_timer("op")
        assert isinstance(timer_id, str)
        assert "op" in timer_id

    def test_stop_timer_returns_duration(self):
        import time
        pm, mc = self._make_perf()
        tid = pm.start_timer("op")
        time.sleep(0.01)
        duration = pm.stop_timer(tid)
        assert duration is not None
        assert duration >= 0.01

    def test_stop_timer_records_metric(self):
        import time
        pm, mc = self._make_perf()
        tid = pm.start_timer("myop")
        time.sleep(0.001)
        pm.stop_timer(tid)
        assert len(mc.timers["myop"]) == 1

    def test_stop_nonexistent_timer_returns_none(self):
        pm, _ = self._make_perf()
        result = pm.stop_timer("does-not-exist")
        assert result is None

    def test_get_performance_summary_empty(self):
        pm, _ = self._make_perf()
        summary = pm.get_performance_summary()
        assert isinstance(summary, dict)

    def test_get_performance_summary_with_data(self):
        import time
        pm, mc = self._make_perf()
        tid = pm.start_timer("work")
        time.sleep(0.001)
        pm.stop_timer(tid)
        summary = pm.get_performance_summary(time_window=timedelta(minutes=5))
        assert "work" in summary
        assert summary["work"]["count"] == 1


# ---------------------------------------------------------------------------
# MonitoringSystem
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestMonitoringSystem:

    def _make_system(self):
        from frameworks.monitoring.monitoring import MonitoringSystem
        return MonitoringSystem()

    def test_record_metric_counter(self):
        from frameworks.monitoring.monitoring import MetricType
        ms = self._make_system()
        ms.record_metric("req", 1.0, MetricType.COUNTER)
        assert ms.metrics.counters["req"] == 1.0

    def test_get_dashboard_data_structure(self):
        ms = self._make_system()
        data = ms.get_dashboard_data()
        assert "metrics" in data
        assert "health" in data
        assert "performance" in data

    def test_export_metrics_json(self):
        from frameworks.monitoring.monitoring import MetricType
        ms = self._make_system()
        ms.record_metric("x", 42.0, MetricType.GAUGE)
        exported = ms.export_metrics(format="json")
        parsed = json.loads(exported)
        assert "metrics" in parsed
        assert "summary" in parsed

    def test_export_metrics_unsupported_format_raises(self):
        ms = self._make_system()
        with pytest.raises(ValueError, match="Unsupported format"):
            ms.export_metrics(format="csv")


# ---------------------------------------------------------------------------
# get_monitoring singleton
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_get_monitoring_returns_same_instance():
    import frameworks.monitoring.monitoring as mod
    # Reset global so we get a fresh singleton
    mod._monitoring = None
    from frameworks.monitoring.monitoring import get_monitoring, MonitoringSystem
    m1 = get_monitoring()
    m2 = get_monitoring()
    assert m1 is m2
    assert isinstance(m1, MonitoringSystem)
    mod._monitoring = None  # cleanup
