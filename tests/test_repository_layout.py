from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_classified_files_have_expected_locations():
    expected = (
        "tests/conftest.py",
        "tests/test_deepseek.py",
        "agent_byte-master/constants.py",
        "experimental/compat/ghostgoat_shim.py",
        "agent_byte-master/agents/creative_module.py",
        "agent_byte-master/agents/custom_analyzer.py",
        "agent_byte-master/services/sentiment_service.py",
    )
    assert all((ROOT / path).is_file() for path in expected)


def test_abandoned_artifacts_and_misplaced_files_are_absent():
    removed = (
        "bots_files.txt",
        "install_upgrades.sh",
        "merge_core.sh",
        "conftest.py",
        "test_deepseek.py",
        "constants.py",
        "ghostgoat_shim.py",
        "creative_module.py",
        "custom_analyzer.py",
        "sentiment_service.py",
    )
    assert all(not (ROOT / path).exists() for path in removed)
