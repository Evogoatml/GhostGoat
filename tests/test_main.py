import main


def test_api_only_dependency_check_does_not_require_node(monkeypatch):
    def unexpected_node_check(*args, **kwargs):
        raise AssertionError("API-only startup must not check for Node.js")

    monkeypatch.setattr(main.subprocess, "run", unexpected_node_check)

    assert main.check_dependencies(require_dashboard=False)
