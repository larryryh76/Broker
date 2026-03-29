import requests
import json
import time
from typing import List, Dict, Optional, Any

def normalize_url(url: str) -> str:
    """V5.3.1 Robust URL Normalization: Fixes duplicates and double slashes."""
    if not url: return ""
    base = "https://www.football.com"

    # 1. Handle Protocol-Relative URLs
    if url.startswith("//"):
        url = "https:" + url

    # 2. If it's already an absolute URL, use it directly (FIX: Avoid duplication)
    if url.startswith("http"):
        # Fix internal double slashes but preserve protocol
        temp_url = url.replace("https://", "HTTPS_TEMP").replace("http://", "HTTP_TEMP")
        while "//" in temp_url: temp_url = temp_url.replace("//", "/")
        return temp_url.replace("HTTPS_TEMP", "https://").replace("HTTP_TEMP", "http://")

    # 3. For relative paths, prepend base
    if not url.startswith("/"):
        url = "/" + url

    return base.rstrip("/") + url

class OmniAPIClient:
    def __init__(self, session_data: Optional[Dict[str, Any]] = None):
        self.session = requests.Session()
        self.headers = {}
        self.cookies = {}
        self.base_url = "https://www.football.com/api/ng/"

        # V5.3 Dynamic Discovery Endpoints
        self.endpoints = {
            "history": None,
            "bet": None,
            "balance": None
        }

        if session_data:
            self.apply_session(session_data)

    def apply_session(self, data: Dict[str, Any]):
        """Applies captured headers, cookies, and endpoint mappings."""
        # V5.10.0: Incremental update (don't overwrite with empty)
        new_headers = data.get("headers", {})
        if new_headers: self.headers.update(new_headers)

        new_cookies = data.get("cookies", [])
        if new_cookies: self.cookies = new_cookies

        # Normalize incoming endpoints before storing
        raw_endpoints = data.get("endpoints", {})
        for key, val in raw_endpoints.items():
            if val:
                normalized = normalize_url(val)
                self.endpoints[key] = normalized
                print(f"DEBUG: Hydrated endpoint [{key}] -> {normalized}")

        # Update session headers
        self.session.headers.update(self.headers)

        # Update session cookies
        for cookie in self.cookies:
            self.session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])

        print(f"DEBUG: V5.3 Session applied with {len([k for k,v in self.endpoints.items() if v])} valid endpoints.")

    def ensure_authenticated(self, user: str, passw: str) -> bool:
        """V5.13.1 Self-Sorting Login: Verifies session or performs direct POST auth."""
        print(f"DEBUG: Ensuring API authentication for {user}...")

        # 1. Test existing session
        try:
            # Simple balance check as health probe
            balance = self.get_balance()
            if balance > 0:
                print("DEBUG: Existing API session valid.")
                return True
        except: pass

        # 2. Perform direct POST login if session invalid
        print("DEBUG: Session invalid or missing. Attempting direct POST login...")
        auth_url = "https://www.football.com/api/ng/auth/login" # Presumed endpoint
        payload = {"mobile": user, "password": passw, "remember": True}

        try:
            response = self.session.post(auth_url, json=payload, timeout=10)
            if response.status_code == 200:
                data = response.json()
                # Capture token if present in body
                token = data.get("token") or data.get("data", {}).get("token")
                if token:
                    self.session.headers.update({"Authorization": f"Bearer {token}"})

                print("DEBUG: API Login successful (POST).")
                return True
            else:
                print(f"DEBUG: API POST Login failed ({response.status_code}).")
        except Exception as e:
            print(f"DEBUG: API Auth Error: {e}")

        return False

    def login(self, user: str, passw: str) -> bool:
        return self.ensure_authenticated(user, passw)

    def get_spin_history(self) -> List[str]:
        """Fetches outcomes from the normalized history endpoint."""
        raw_url = self.endpoints.get("history")
        if not raw_url:
            print("WARNING: History endpoint not yet discovered.")
            return []

        final_url = normalize_url(raw_url)
        print(f"DEBUG: Calling history endpoint -> {final_url}")

        try:
            response = self.session.get(final_url, timeout=10)
            if response.status_code == 200:
                print(f"DEBUG: History Response Preview: {response.text[:500]}")
                data = response.json()
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
                print(f"DEBUG: History fetch failed. Status: {response.status_code} | URL: {final_url}")
        except Exception as e:
            print(f"DEBUG: Error fetching spin history: {e}")
        return []

    def place_bet(self, direction: str, amount: float) -> Dict[str, Any]:
        """Places a bet via the normalized betting endpoint."""
        raw_url = self.endpoints.get("bet")
        if not raw_url: return {"error": "Bet endpoint not discovered."}

        final_url = normalize_url(raw_url)
        print(f"DEBUG: Calling bet endpoint -> {final_url}")

        try:
            payload = {
                "direction": "UP" if direction == "U" else "DOWN",
                "amount": amount,
                "timestamp": int(time.time() * 1000)
            }
            response = self.session.post(final_url, json=payload, timeout=10)
            return response.json() if response.status_code == 200 else {"error": response.status_code}
        except Exception as e:
            return {"error": str(e)}

    def get_balance(self) -> float:
        """Fetches balance from the normalized balance endpoint."""
        raw_url = self.endpoints.get("balance")
        if not raw_url: return 0.0

        final_url = normalize_url(raw_url)
        print(f"DEBUG: Calling balance endpoint -> {final_url}")

        try:
            res = self.session.get(final_url, timeout=10)
            if res.status_code == 200:
                data = res.json()
                return float(data.get("balance") or data.get("amount") or data.get("available", 0.0))
        except: pass
        return 0.0
