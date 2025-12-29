import requests

class APIPlugin:
    """Generic API connector plugin for ADAP."""

    def __init__(self):
        # optional: you can load from env or config later
        self.default_base = "https://api.example.com"

    def execute(self, endpoint="", method="GET", params=None, data=None, headers=None):
        """Call a REST endpoint.
        Args:
            endpoint (str): endpoint path, e.g. 'users'
            method (str): HTTP verb
            params (dict): query params
            data (dict): JSON body
            headers (dict): optional headers
        """
        url = f"{self.default_base.rstrip('/')}/{endpoint.lstrip('/')}"
        try:
            resp = requests.request(
                method=method.upper(),
                url=url,
                params=params,
                json=data,
                headers=headers,
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"error": str(e)}
