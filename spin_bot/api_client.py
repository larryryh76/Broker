import requests
import json
import time
from typing import List, Dict, Optional, Any

def normalize_url(url: str) -> str:
    if not url: return ""
    base = "https://www.football.com"
    if url.startswith("//"): url = "https:" + url
    if url.startswith("http"):
        temp = url.replace("https://", "HTTPS_TEMP").replace("http://", "HTTP_TEMP")
        while "//" in temp: temp = temp.replace("//", "/")
        return temp.replace("HTTPS_TEMP", "https://").replace("HTTP_TEMP", "http://")
    if not url.startswith("/"): url = "/" + url
    return base.rstrip("/") + url

class OmniAPIClient:
    def __init__(self, session_data: Optional[Dict[str, Any]] = None):
        self.session = requests.Session()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1",
            "Origin": "https://www.football.com",
            "Referer": "https://www.football.com/ng/m/independent_login",
            "Accept": "application/json"
        }
        self.session.headers.update(self.headers)
        self.endpoints = {"history": None, "bet": None, "balance": None}
        if session_data: self.apply_session(session_data)

    def apply_session(self, data: Dict[str, Any]):
        new_headers = data.get("headers", {})
        self.headers.update(new_headers)

        auth_state = data.get("auth_state", {})
        if auth_state.get("accessToken"):
            self.headers["accessToken"] = auth_state["accessToken"]
            self.headers["Authorization"] = f"Bearer {auth_state['accessToken']}"
        if auth_state.get("puid"):
            self.headers["puid"] = auth_state["puid"]

        self.session.headers.update(self.headers)

        new_cookies = data.get("cookies", [])
        for cookie in new_cookies:
            self.session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])

        raw_endpoints = data.get("endpoints", {})
        for key, val in raw_endpoints.items():
            if val: self.endpoints[key] = normalize_url(val)

    def get_spin_history(self) -> List[str]:
        raw_url = self.endpoints.get("history")
        if not raw_url: return []
        try:
            res = self.session.get(normalize_url(raw_url), timeout=10)
            if res.status_code == 200:
                data = res.json()
                items = data if isinstance(data, list) else data.get("results", data.get("spins", []))
                outcomes = []
                for item in items:
                    val = item.get("outcome") if isinstance(item, dict) else item
                    if val: outcomes.append(str(val).upper()[0])
                return outcomes[::-1]
        except: pass
        return []
