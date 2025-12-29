import os, json, requests

class APIManager:
    CONNECTOR_DIR = "/root/adap/connectors"

    def __init__(self):
        os.makedirs(self.CONNECTOR_DIR, exist_ok=True)
        self.apis = {}
        self._load_all()

    # -------- Core ops --------
    def _load_all(self):
        for f in os.listdir(self.CONNECTOR_DIR):
            if f.endswith(".json"):
                try:
                    with open(os.path.join(self.CONNECTOR_DIR, f)) as fh:
                        cfg = json.load(fh)
                        self.apis[cfg["name"].lower()] = cfg
                except Exception as e:
                    print(f"[skip] {f}: {e}")

    def add_api(self, name, base_url, api_key=None, headers=None):
        cfg = {
            "name": name.lower(),
            "base_url": base_url.strip(),
            "headers": headers or {},
        }
        if api_key:
            cfg["headers"]["Authorization"] = f"Bearer {api_key}"
        path = os.path.join(self.CONNECTOR_DIR, f"{cfg['name']}.json")
        with open(path, "w") as f:
            json.dump(cfg, f, indent=2)
        self.apis[cfg["name"].lower()] = cfg
        print(f"[saved] {path}")

    def remove_api(self, name):
        name = name.lower()
        path = os.path.join(self.CONNECTOR_DIR, f"{name}.json")
        if os.path.exists(path):
            os.remove(path)
        self.apis.pop(name, None)
        print(f"[removed] {name}")

    def execute(self, api_name, endpoint="", method="GET", params=None, data=None):
        api = self.apis.get(api_name.lower())
        if not api:
            return {"error": f"API '{api_name}' not found"}
        url = f"{api['base_url'].rstrip('/')}/{endpoint.lstrip('/')}"
        try:
            r = requests.request(
                method=method.upper(),
                url=url,
                params=params,
                json=data,
                headers=api.get("headers", {}),
                timeout=15,
            )
            r.raise_for_status()
            return r.json()
        except Exception as e:
            return {"error": str(e)}

    def export_all(self):
        export_path = "/root/adap/api_backup.json"
        with open(export_path, "w") as f:
            json.dump(self.apis, f, indent=2)
        print(f"[exported] → {export_path}")

    def import_all(self, path):
        with open(path) as f:
            imported = json.load(f)
        for name, cfg in imported.items():
            self.add_api(cfg["name"], cfg["base_url"], headers=cfg.get("headers"))
        print(f"[imported] {len(imported)} APIs")

    def list_apis(self):
        if not self.apis:
            print("No APIs registered.")
            return
        for i, n in enumerate(self.apis, start=1):
            print(f"{i}. {n} → {self.apis[n]['base_url']}")

# -------- Menu UI --------
def main():
    m = APIManager()

    while True:
        print("""
╔════════════════════════════════╗
║         ADAP API MANAGER       ║
╠════════════════════════════════╣
║ 1. List APIs                   ║
║ 2. Add new API                 ║
║ 3. Remove API                  ║
║ 4. Execute API call            ║
║ 5. Export all APIs             ║
║ 6. Import APIs from file       ║
║ 7. Exit                        ║
╚════════════════════════════════╝
""")
        choice = input("Select option: ").strip()

        if choice == "1":
            m.list_apis()

        elif choice == "2":
            name = input("API name: ").strip()
            base = input("Base URL: ").strip()
            key = input("API key (optional): ").strip()
            m.add_api(name, base, key)

        elif choice == "3":
            name = input("API name to remove: ").strip()
            m.remove_api(name)

        elif choice == "4":
            name = input("API name: ").strip()
            endpoint = input("Endpoint (e.g. /get): ").strip()
            method = input("Method [GET/POST]: ").strip().upper() or "GET"
            res = m.execute(name, endpoint, method)
            print(json.dumps(res, indent=2))

        elif choice == "5":
            m.export_all()

        elif choice == "6":
            path = input("Path to import JSON: ").strip()
            m.import_all(path)

        elif choice == "7":
            print("Goodbye.")
            break
        else:
            print("Invalid selection.")

if __name__ == "__main__":
    main()
