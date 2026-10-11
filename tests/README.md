# Tests

This directory contains the GhostGoat pytest suite and its shared `conftest.py`
configuration, which adds the repository and Agent Byte source roots to imports.
Tests are discovered from this directory by `.pytest.ini`.
`test_deepseek.py` is an optional integration test that uses `DEEPSEEK_API_KEY`
when available.
