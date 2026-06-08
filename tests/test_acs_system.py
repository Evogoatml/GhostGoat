"""
Tests for ACS_SYSTEM modules:
  - adap_pipeline/crypto.py    — encrypt / sign_log
  - adap_pipeline/policy.py    — choose_cipher
  - core/anomaly_detector.py   — AnomalyDetector
  - core/metrics_collector.py  — MetricsCollector
"""

import asyncio
import base64
import json
import os
import pytest
from collections import deque
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_metrics(mem_pct=50.0, cpu_avg=30.0, disk_pct=60.0):
    """Build a minimal metrics dict matching the expected schema."""
    return {
        "timestamp": datetime.now().isoformat(),
        "system": {
            "memory": {"percent": mem_pct, "virtual": {"percent": mem_pct}},
            "cpu": {"avg": cpu_avg, "percent": [cpu_avg]},
            "temperature": {},
        },
        "disk": {"/": {"percent": disk_pct}},
        "processes": {},
        "network": {},
    }


# ===========================================================================
# adap_pipeline/crypto.py
# ===========================================================================

class TestEncrypt:
    def test_encrypt_returns_bytes(self):
        from ACS_SYSTEM.adap_dia_sys.crypto import GhostGoatCrypto
        crypto = GhostGoatCrypto()
        result, _ = crypto.encrypt(b"hello world", "aesgcm")
        assert isinstance(result, bytes)

    def test_encrypt_aesgcm_produces_ciphertext(self):
        from ACS_SYSTEM.adap_dia_sys.crypto import GhostGoatCrypto
        crypto = GhostGoatCrypto()
        plaintext = b"secret data"
        ciphertext, _ = crypto.encrypt(plaintext, "aesgcm")
        assert ciphertext != plaintext

    def test_encrypt_chacha20_returns_bytes(self):
        from ACS_SYSTEM.adap_dia_sys.crypto import GhostGoatCrypto
        crypto = GhostGoatCrypto()
        result, _ = crypto.encrypt(b"test payload", "chacha20poly1305")
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_encrypt_different_calls_different_ciphertexts(self):
        from ACS_SYSTEM.adap_dia_sys.crypto import GhostGoatCrypto
        crypto = GhostGoatCrypto()
        c1, _ = crypto.encrypt(b"same", "aesgcm")
        c2, _ = crypto.encrypt(b"same", "aesgcm")
        assert c1 != c2

    def test_encrypt_unknown_cipher_raises(self):
        from ACS_SYSTEM.adap_dia_sys.crypto import GhostGoatCrypto
        crypto = GhostGoatCrypto()
        with pytest.raises(Exception):
            crypto.encrypt(b"data", "unknown_cipher")


class TestSignLog:
    def test_sign_log_adds_signature(self, tmp_path):
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from ACS_SYSTEM.adap_dia_sys.crypto import GhostGoatCrypto

        crypto = GhostGoatCrypto()
        priv_bytes, _ = crypto.generate_keypair()
        keyfile = tmp_path / "privkey.pem"
        keyfile.write_bytes(priv_bytes)

        entry = {"event": "test", "value": 42}
        result = crypto.sign_log(entry, privkey_path=str(keyfile))

        assert "signature" in result
        assert isinstance(result["signature"], str)

    def test_sign_log_signature_is_base64(self, tmp_path):
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from ACS_SYSTEM.adap_dia_sys.crypto import GhostGoatCrypto

        crypto = GhostGoatCrypto()
        priv_bytes, _ = crypto.generate_keypair()
        keyfile = tmp_path / "privkey.pem"
        keyfile.write_bytes(priv_bytes)

        entry = {"event": "audit"}
        result = crypto.sign_log(entry, privkey_path=str(keyfile))

        decoded = base64.b64decode(result["signature"])
        assert len(decoded) == 64  # Ed25519 signature is always 64 bytes

    def test_sign_log_modifies_entry_in_place(self, tmp_path):
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from ACS_SYSTEM.adap_dia_sys.crypto import GhostGoatCrypto

        crypto = GhostGoatCrypto()
        priv_bytes, _ = crypto.generate_keypair()
        keyfile = tmp_path / "privkey.pem"
        keyfile.write_bytes(priv_bytes)

        entry = {"data": "value"}
        result = crypto.sign_log(entry, privkey_path=str(keyfile))

        assert result is entry  # same dict, mutated

    def test_sign_log_raises_if_key_missing(self):
        from ACS_SYSTEM.adap_dia_sys.crypto import GhostGoatCrypto
        crypto = GhostGoatCrypto()
        with pytest.raises(Exception):
            crypto.sign_log({"x": 1}, privkey_path="/nonexistent/key.pem")


# ===========================================================================
# adap_pipeline/policy.py
# ===========================================================================

class TestChooseCipher:
    def test_chooses_chacha_when_cpu_over_limit(self):
        from ACS_SYSTEM.adap_dia_sys.policy import choose_cipher
        result = choose_cipher({"cpu": 80}, {"CPU_LIMIT": "60"})
        assert result == "chacha20poly1305"

    def test_chooses_aesgcm_when_cpu_under_limit(self):
        from ACS_SYSTEM.adap_dia_sys.policy import choose_cipher
        result = choose_cipher({"cpu": 40}, {"CPU_LIMIT": "60"})
        assert result == "aesgcm"

    def test_chooses_aesgcm_at_limit(self):
        from ACS_SYSTEM.adap_dia_sys.policy import choose_cipher
        result = choose_cipher({"cpu": 60}, {"CPU_LIMIT": "60"})
        assert result == "aesgcm"

    def test_default_cpu_limit_60(self):
        from ACS_SYSTEM.adap_dia_sys.policy import choose_cipher
        result = choose_cipher({"cpu": 70}, {})
        assert result == "chacha20poly1305"

    def test_default_cpu_limit_low_cpu(self):
        from ACS_SYSTEM.adap_dia_sys.policy import choose_cipher
        result = choose_cipher({"cpu": 10}, {})
        assert result == "aesgcm"

    def test_custom_high_limit(self):
        from ACS_SYSTEM.adap_dia_sys.policy import choose_cipher
        result = choose_cipher({"cpu": 80}, {"CPU_LIMIT": "90"})
        assert result == "aesgcm"


# ===========================================================================
# core/anomaly_detector.py
# ===========================================================================

@pytest.fixture
def detector():
    from ACS_SYSTEM.core.anomaly_detector import AnomalyDetector
    config = {
        "thresholds": {
            "memory_critical": 90,
            "memory_warning": 80,
            "cpu_critical": 95,
            "disk_critical": 95,
        }
    }
    return AnomalyDetector(config)


class TestAnomalyDetectorInit:
    def test_default_history_maxlen(self, detector):
        assert detector.history.maxlen == 1000

    def test_baseline_empty_initially(self, detector):
        assert detector.baseline == {}

    def test_learning_period(self, detector):
        assert detector.learning_period == 100


class TestCheckStaticThresholds:
    def test_memory_critical_detected(self, detector):
        metrics = _make_metrics(mem_pct=92.0)
        anomalies = detector.check_static_thresholds(metrics)
        types = [a["type"] for a in anomalies]
        assert "memory_critical" in types

    def test_memory_warning_detected(self, detector):
        metrics = _make_metrics(mem_pct=85.0)
        anomalies = detector.check_static_thresholds(metrics)
        types = [a["type"] for a in anomalies]
        assert "memory_warning" in types

    def test_memory_ok_no_anomaly(self, detector):
        metrics = _make_metrics(mem_pct=50.0)
        anomalies = detector.check_static_thresholds(metrics)
        types = [a["type"] for a in anomalies]
        assert "memory_critical" not in types
        assert "memory_warning" not in types

    def test_cpu_critical_detected(self, detector):
        metrics = _make_metrics(cpu_avg=97.0)
        anomalies = detector.check_static_thresholds(metrics)
        types = [a["type"] for a in anomalies]
        assert "cpu_critical" in types

    def test_cpu_ok_no_anomaly(self, detector):
        metrics = _make_metrics(cpu_avg=50.0)
        anomalies = detector.check_static_thresholds(metrics)
        types = [a["type"] for a in anomalies]
        assert "cpu_critical" not in types

    def test_disk_critical_detected(self, detector):
        metrics = _make_metrics(disk_pct=97.0)
        anomalies = detector.check_static_thresholds(metrics)
        types = [a["type"] for a in anomalies]
        assert "disk_critical" in types

    def test_anomalies_have_timestamp(self, detector):
        metrics = _make_metrics(mem_pct=95.0)
        anomalies = detector.check_static_thresholds(metrics)
        for a in anomalies:
            assert "timestamp" in a

    def test_anomalies_have_severity(self, detector):
        metrics = _make_metrics(mem_pct=95.0)
        anomalies = detector.check_static_thresholds(metrics)
        for a in anomalies:
            assert "severity" in a


class TestDetectMethod:
    def test_detect_returns_list(self, detector):
        result = detector.detect(_make_metrics())
        assert isinstance(result, list)

    def test_detect_appends_to_history(self, detector):
        detector.detect(_make_metrics())
        assert len(detector.history) == 1

    def test_detect_multiple_calls_accumulate_history(self, detector):
        for _ in range(5):
            detector.detect(_make_metrics())
        assert len(detector.history) == 5

    def test_detect_critical_memory(self, detector):
        result = detector.detect(_make_metrics(mem_pct=92.0))
        types = [a["type"] for a in result]
        assert "memory_critical" in types


class TestDetectMemoryLeak:
    def test_returns_false_insufficient_history(self, detector):
        # Less than 50 entries
        for i in range(10):
            detector.history.append(_make_metrics(mem_pct=50.0))
        assert detector.detect_memory_leak() is False

    def test_returns_true_on_increasing_trend(self, detector):
        # 50 samples with steadily increasing memory
        for i in range(50):
            detector.history.append(_make_metrics(mem_pct=50.0 + i * 1.5))
        assert detector.detect_memory_leak() == True

    def test_returns_false_on_stable_memory(self, detector):
        for _ in range(50):
            detector.history.append(_make_metrics(mem_pct=50.0))
        assert detector.detect_memory_leak() == False


class TestDetectCpuThrashing:
    def test_returns_false_insufficient_history(self, detector):
        for i in range(5):
            detector.history.append(_make_metrics(cpu_avg=80.0))
        assert detector.detect_cpu_thrashing() is False

    def test_returns_true_high_avg_high_variance(self, detector):
        # Alternating 50/99 → avg ~74.5, std ~24.5 → satisfies avg>70 and std>20
        values = [50.0, 99.0] * 15
        for v in values:
            detector.history.append(_make_metrics(cpu_avg=v))
        assert detector.detect_cpu_thrashing() == True

    def test_returns_false_low_cpu(self, detector):
        for _ in range(30):
            detector.history.append(_make_metrics(cpu_avg=20.0))
        assert detector.detect_cpu_thrashing() == False


class TestUpdateBaseline:
    def test_baseline_updated_after_100_samples(self, detector):
        for i in range(100):
            detector.history.append(_make_metrics(mem_pct=50.0 + (i % 10), cpu_avg=30.0))
        detector.update_baseline()
        assert "memory_mean" in detector.baseline
        assert "cpu_mean" in detector.baseline
        assert "memory_std" in detector.baseline

    def test_baseline_values_are_floats(self, detector):
        for _ in range(100):
            detector.history.append(_make_metrics(mem_pct=60.0, cpu_avg=40.0))
        detector.update_baseline()
        for key, val in detector.baseline.items():
            assert isinstance(val, float), f"{key} should be float"


# ===========================================================================
# core/metrics_collector.py
# ===========================================================================

@pytest.fixture
def metrics_collector():
    from ACS_SYSTEM.core.metrics_collector import MetricsCollector
    config = {"cache_ttl": 5}
    return MetricsCollector(config)


def _run(coro):
    return asyncio.run(coro)


class TestMetricsCollectorInit:
    def test_config_stored(self, metrics_collector):
        assert metrics_collector.config["cache_ttl"] == 5

    def test_cache_initially_empty(self, metrics_collector):
        assert metrics_collector.cache == {}

    def test_cache_ttl(self, metrics_collector):
        assert metrics_collector.cache_ttl == 5

    def test_custom_cache_ttl(self):
        from ACS_SYSTEM.core.metrics_collector import MetricsCollector
        c = MetricsCollector({"cache_ttl": 30})
        assert c.cache_ttl == 30

    def test_default_cache_ttl(self):
        from ACS_SYSTEM.core.metrics_collector import MetricsCollector
        c = MetricsCollector({})
        assert c.cache_ttl == 5


class TestCollectSystemMetrics:
    def test_returns_cpu_memory_temperature(self, metrics_collector):
        mock_psutil = MagicMock()
        mock_psutil.cpu_percent.return_value = [10.0, 15.0]
        mock_psutil.cpu_count.return_value = 2
        mock_psutil.cpu_freq.return_value = None
        mem = MagicMock()
        mem.percent = 45.0
        mem._asdict.return_value = {"percent": 45.0, "used": 1000}
        mock_psutil.virtual_memory.return_value = mem
        swap = MagicMock()
        swap._asdict.return_value = {"percent": 5.0}
        mock_psutil.swap_memory.return_value = swap
        mock_psutil.getloadavg.return_value = (0.5, 0.4, 0.3)
        mock_psutil.sensors_temperatures.return_value = {}

        with patch("ACS_SYSTEM.core.metrics_collector.psutil", mock_psutil):
            result = _run(metrics_collector.collect_system_metrics())

        assert "cpu" in result
        assert "memory" in result
        assert "temperature" in result

    def test_cpu_has_avg(self, metrics_collector):
        mock_psutil = MagicMock()
        mock_psutil.cpu_percent.return_value = [20.0, 40.0]
        mock_psutil.cpu_count.return_value = 2
        mock_psutil.cpu_freq.return_value = None
        mem = MagicMock()
        mem.percent = 50.0
        mem._asdict.return_value = {"percent": 50.0}
        mock_psutil.virtual_memory.return_value = mem
        mock_psutil.swap_memory.return_value = MagicMock(_asdict=lambda: {})
        mock_psutil.getloadavg.return_value = (1.0, 1.0, 1.0)
        mock_psutil.sensors_temperatures.return_value = {}

        with patch("ACS_SYSTEM.core.metrics_collector.psutil", mock_psutil):
            result = _run(metrics_collector.collect_system_metrics())

        assert result["cpu"]["avg"] == 30.0  # (20+40)/2


class TestCollectCustomMetrics:
    def test_returns_uptime_and_timestamp(self, metrics_collector):
        mock_psutil = MagicMock()
        mock_psutil.boot_time.return_value = 1234567890.0

        with patch("ACS_SYSTEM.core.metrics_collector.psutil", mock_psutil):
            result = _run(metrics_collector.collect_custom_metrics())

        assert "uptime" in result
        assert "timestamp" in result

    def test_uptime_is_numeric(self, metrics_collector):
        mock_psutil = MagicMock()
        mock_psutil.boot_time.return_value = 9999.0

        with patch("ACS_SYSTEM.core.metrics_collector.psutil", mock_psutil):
            result = _run(metrics_collector.collect_custom_metrics())

        assert isinstance(result["uptime"], float)


class TestGetUptime:
    def test_returns_boot_time(self, metrics_collector):
        mock_psutil = MagicMock()
        mock_psutil.boot_time.return_value = 12345.0
        with patch("ACS_SYSTEM.core.metrics_collector.psutil", mock_psutil):
            result = metrics_collector.get_uptime()
        assert result == 12345.0


class TestGetTemperature:
    def test_returns_dict(self, metrics_collector):
        mock_psutil = MagicMock()
        mock_psutil.sensors_temperatures.return_value = {}
        with patch("ACS_SYSTEM.core.metrics_collector.psutil", mock_psutil):
            result = _run(metrics_collector.get_temperature())
        assert isinstance(result, dict)

    def test_handles_sensor_exception(self, metrics_collector):
        mock_psutil = MagicMock()
        mock_psutil.sensors_temperatures.side_effect = AttributeError("no sensors")
        with patch("ACS_SYSTEM.core.metrics_collector.psutil", mock_psutil):
            result = _run(metrics_collector.get_temperature())
        assert result == {}


class TestCollectDiskMetrics:
    def test_returns_dict_per_mount(self, metrics_collector):
        mock_psutil = MagicMock()
        part = MagicMock()
        part.mountpoint = "/"
        usage = MagicMock()
        usage._asdict.return_value = {"percent": 55.0, "total": 100}
        mock_psutil.disk_partitions.return_value = [part]
        mock_psutil.disk_usage.return_value = usage

        with patch("ACS_SYSTEM.core.metrics_collector.psutil", mock_psutil):
            result = _run(metrics_collector.collect_disk_metrics())

        assert "/" in result
        assert result["/"]["percent"] == 55.0

    def test_handles_permission_error(self, metrics_collector):
        mock_psutil = MagicMock()
        part = MagicMock()
        part.mountpoint = "/restricted"
        mock_psutil.disk_partitions.return_value = [part]
        mock_psutil.disk_usage.side_effect = PermissionError()

        with patch("ACS_SYSTEM.core.metrics_collector.psutil", mock_psutil):
            result = _run(metrics_collector.collect_disk_metrics())

        assert "/restricted" not in result


class TestCollectNetworkMetrics:
    def test_returns_io_and_connections(self, metrics_collector):
        mock_psutil = MagicMock()
        net_io = MagicMock()
        net_io._asdict.return_value = {"bytes_sent": 1000, "bytes_recv": 2000}
        mock_psutil.net_io_counters.return_value = net_io

        conn_established = MagicMock()
        conn_established.status = "ESTABLISHED"
        conn_listen = MagicMock()
        conn_listen.status = "LISTEN"
        mock_psutil.net_connections.return_value = [conn_established, conn_listen]

        with patch("ACS_SYSTEM.core.metrics_collector.psutil", mock_psutil):
            result = _run(metrics_collector.collect_network_metrics())

        assert "io" in result
        assert "connections" in result
        assert result["connections"]["established"] == 1
        assert result["connections"]["listen"] == 1
        assert result["connections"]["total"] == 2
