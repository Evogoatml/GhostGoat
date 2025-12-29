#!/usr/bin/env python3
# modules/diagnostics/external_services.py

from modules.governance.decision_governor import allow_external_calls
from modules.public_api_connector import fetch_api_list


class ExternalIntelligenceService:
    """Facade for external intelligence operations.

    This class isolates network/API interactions from UI and local logic.
    """

    def sync(self, force: bool = False):
        """Synchronize external intelligence data.

        Raises:
            PermissionError: If policy prohibits external calls for this context.
            Exception: Propagates exceptions from the underlying connector.
        Returns:
            dict: Data returned from the external API or cache.
        """
        if not allow_external_calls("diagnostic"):
            raise PermissionError("External data sync not permitted by policy")
        return fetch_api_list(force=force)
