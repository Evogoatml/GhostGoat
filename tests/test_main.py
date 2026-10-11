import main


def test_main_is_the_single_entry_point():
    assert callable(main.main)
    assert callable(main.run)
    assert not hasattr(main, "run_api_only")
    assert not hasattr(main, "check_dependencies")
