class SamplePlugin:
    """Example plugin demonstrating required interface."""
    def execute(self, *args, **kwargs):
        print("[SamplePlugin] Executed with args:", args, "kwargs:", kwargs)
