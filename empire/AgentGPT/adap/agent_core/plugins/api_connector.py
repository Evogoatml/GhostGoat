import json, os, requests

class APIConnector:
    """Loads API definitions from /root/adap/connectors/*.json and executes them."""
    CONNECTOR_DIR = "/root/adap/connectors"

    def __init__(self):
        self.apis = {}
        self._load_all()

    def _load_all(self):
        if not os.path.isdir(self.CONNECTOR_DIR):
            os.makedirs(self.CONNECTOR_DIR, exist_ok=True)
        for f in os.listdir(self.CONNECTOR_DIR):
            if f.endswith(".json"):
                try:
                    with open(os.path.join(self.CONNECTOR_DIR, f)) as fh:
                        cfg = json.load(fh)
                        self.apis[cfg["name"].lower()] = cfg
                except Exception as e:
                    print(f"[skip] {f}: {e}")

    def execute(self, api_name, endpoint="", method="GET", params=None, data=None):
        api = self.apis.get(api_name.lower())
        if not api:
            return {"error": f"API '{api_name}' not found"}
        url = f"{api['base_url'].rstrip('/')}/{endpoint.lstrip('/')}"
        headers = api.get("headers", {})
        try:
            r = requests.request(
                method=method.upper(),
                url=url,
                params=params,
                json=data,
                headers=headers,
                timeout=10,
            )
            r.raise_for_status()
            return r.json()
        except Exception as e:
            return {"error": str(e)}

# --- Auto test run when executed directly ---
if __name__ == "__main__":
    connector = APIConnector()
    result = connector.execute("httpbin", "get", params={"ping": "ok"})
    print(result)
