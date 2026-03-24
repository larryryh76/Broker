import requests
import json
import time
from typing import List, Dict, Optional, Any

def normalize_url(url: str, base_url: str) -> str:
    """Correctly handles relative and absolute URLs."""
    if not url:
        return ""
    if url.startswith("http"):
        return url
    if url.startswith("//"):
        return "https:" + url
    return base_url.rstrip("/") + "/" + url.lstrip("/")

class OmniAPIClient:
    def __init__(self, session_data: Optional[Dict[str, Any]] = None):
        self.session = requests.Session()
        self.headers = {}
        self.cookies = {}
        self.base_url = "https://www.football.com/api/ng/"

        # V5.0 Dynamic Discovery Endpoints
        self.endpoints = {
            "history": None,
            "bet": None,
            "balance": None
        }

        if session_data:
            self.apply_session(session_data)

    def apply_session(self, data: Dict[str, Any]):
        """Applies captured headers, cookies, and endpoint mappings."""
        self.headers = data.get("headers", {})
        self.cookies = data.get("cookies", {})
        self.endpoints.update(data.get("endpoints", {}))

        # Update session headers
        self.session.headers.update(self.headers)

        # Update session cookies
        for cookie in self.cookies:
            self.session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])

        print(f"DEBUG: Session and {len([k for k,v in self.endpoints.items() if v])} endpoints applied.")

    def get_spin_history(self) -> List[str]:
        """Fetches outcomes from the dynamically discovered history endpoint."""
        raw_url = self.endpoints.get("history")
        if not raw_url:
            print("WARNING: History endpoint not yet discovered.")
            return []

        final_url = normalize_url(raw_url, self.base_url)
        print(f"DEBUG: Calling history endpoint -> {final_url}")

        try:
            response = self.session.get(final_url, timeout=10)
            if response.status_code == 200:
                print(f"DEBUG: History Response Preview: {response.text[:500]}")
                data = response.json()

                # V5.2 Refined Outcome Extraction
                # Supports both { results: [...] } and [ { outcome: ... } ]
                items = data if isinstance(data, list) else data.get("results", data.get("spins", []))
                outcomes = []
                for item in items:
                    val = None
                    if isinstance(item, dict):
                        val = item.get("outcome") or item.get("result") or item.get("val")
                    elif isinstance(item, str):
                        val = item

                    if val:
                        char = str(val).upper()[0]
                        if char in ["U", "D"]:
                            outcomes.append(char)
                return outcomes
            else:
                print(f"DEBUG: History fetch failed. Status: {response.status_code} | Text: {response.text}")
        except Exception as e:
            print(f"DEBUG: Error fetching spin history: {e}")
        return []

    def place_bet(self, direction: str, amount: float) -> Dict[str, Any]:
        """Places a bet via the dynamically discovered betting endpoint."""
        raw_url = self.endpoints.get("bet")
        if not raw_url:
            return {"error": "Bet endpoint not discovered."}

        final_url = normalize_url(raw_url, self.base_url)
        print(f"DEBUG: Calling bet endpoint -> {final_url}")

        try:
            payload = {
                "direction": "UP" if direction == "U" else "DOWN",
                "amount": amount,
                "timestamp": int(time.time() * 1000)
            }
            response = self.session.post(final_url, json=payload, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"DEBUG: Bet failed. Status: {response.status_code} | Text: {response.text}")
                return {"error": response.status_code, "text": response.text}
        except Exception as e:
            return {"error": str(e)}

    def get_balance(self) -> float:
        """Fetches balance from the dynamically discovered balance endpoint."""
        raw_url = self.endpoints.get("balance")
        if not raw_url: return 0.0

        final_url = normalize_url(raw_url, self.base_url)
        print(f"DEBUG: Calling balance endpoint -> {final_url}")

        try:
            res = self.session.get(final_url, timeout=10)
            if res.status_code == 200:
                data = res.json()
                return float(data.get("balance") or data.get("amount") or data.get("available", 0.0))
            else:
                print(f"DEBUG: Balance fetch failed. Status: {res.status_code}")
        except: pass
        return 0.0
