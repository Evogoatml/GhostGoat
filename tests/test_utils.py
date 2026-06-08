"""
Unit tests for utils.get_logger()
"""

import logging
import os
import pytest


@pytest.mark.unit
class TestGetLogger:

    def test_returns_logger(self):
        from utils import get_logger
        log = get_logger("test.basic")
        assert isinstance(log, logging.Logger)

    def test_logger_name(self):
        from utils import get_logger
        log = get_logger("test.name_check")
        assert log.name == "test.name_check"

    def test_default_level_is_info(self):
        from utils import get_logger
        log = get_logger("test.default_level")
        assert log.level == logging.INFO

    def test_custom_log_level(self):
        from utils import get_logger
        log = get_logger("test.debug_level", log_level="DEBUG")
        assert log.level == logging.DEBUG

    def test_unknown_level_falls_back_to_info(self):
        from utils import get_logger
        log = get_logger("test.unknown_level", log_level="NOTAREALEVEL")
        # getattr with fallback to INFO
        assert log.level == logging.INFO

    def test_console_handler_added(self):
        from utils import get_logger
        log = get_logger("test.has_console_handler")
        handler_types = [type(h) for h in log.handlers]
        assert logging.StreamHandler in handler_types

    def test_idempotent_no_duplicate_handlers(self):
        """Calling get_logger twice with the same name must not add more handlers."""
        from utils import get_logger
        log = get_logger("test.idempotent")
        count_first = len(log.handlers)
        get_logger("test.idempotent")
        assert len(log.handlers) == count_first

    def test_file_handler_created(self, tmp_path):
        from utils import get_logger
        log_file = str(tmp_path / "subdir" / "test.log")
        log = get_logger("test.file_handler", log_file=log_file)
        handler_types = [type(h) for h in log.handlers]
        assert logging.FileHandler in handler_types
        assert os.path.exists(log_file)

    def test_file_handler_creates_parent_dirs(self, tmp_path):
        from utils import get_logger
        log_file = str(tmp_path / "deep" / "nested" / "dir" / "test.log")
        get_logger("test.nested_dirs", log_file=log_file)
        assert os.path.exists(log_file)
