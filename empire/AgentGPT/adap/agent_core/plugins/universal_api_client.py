"""
Universal API client for adap agent
@jarviscmd: Call any HTTP API with custom endpoint and API key.
"""

import requests

def run():
    url = input("API endpoint URL: ")
    api_key = input("API key (leave blank if none): ")
    params = input("Extra query params (e.g. key1=val1&key2=val2, blank for none): ")
    headers = {}
    if api_key:
        # Common for apilayer: apikey in header or as query
        headers["apikey"] = api_key

    full_url = url
    if params:
        sep = "&" if "?" in url else "?"
        full_url = f"{url}{sep}{params}"
    print(f"Requesting: {full_url}")
    resp = requests.get(full_url, headers=headers)
    print("Status:", resp.status_code)
    print("Result:\n", resp.text)
