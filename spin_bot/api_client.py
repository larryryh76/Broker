import requests
import json
import time
from typing import List, Dict, Optional, Any

class OmniAPIClient:
    def __init__(self, session_data: Optional[Dict[str, Any]] = None):
        self.session = requests.Session()
        self.headers = {}
        self.cookies = {}

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
        endpoint = self.endpoints.get("history")
        if not endpoint:
            print("WARNING: History endpoint not yet discovered.")
            return []

        try:
            response = self.session.get(endpoint, timeout=10)
            if response.status_code == 200:
                data = response.json()
                # Generalized outcome extraction
                raw = json.dumps(data).upper()
                outcomes = []
                for char in raw:
                    if char in ["U", "D"]: outcomes.append(char)
                    if len(outcomes) > 20: break
                return outcomes
            elif response.status_code == 403:
                print("DEBUG: API 403. Session Expired.")
        except: pass
        return []

    def place_bet(self, direction: str, amount: float) -> Dict[str, Any]:
        """Places a bet via the dynamically discovered betting endpoint."""
        endpoint = self.endpoints.get("bet")
        if not endpoint:
            return {"error": "Bet endpoint not discovered."}

        try:
            payload = {
                "direction": "UP" if direction == "U" else "DOWN",
                "amount": amount,
                "timestamp": int(time.time() * 1000)
            }
            response = self.session.post(endpoint, json=payload, timeout=10)
            return response.json() if response.status_code == 200 else {"error": response.status_code}
        except Exception as e:
            return {"error": str(e)}

    def get_balance(self) -> float:
        """Fetches balance from the dynamically discovered balance endpoint."""
        endpoint = self.endpoints.get("balance")
        if not endpoint: return 0.0
        try:
            res = self.session.get(endpoint, timeout=10)
            if res.status_code == 200:
                return float(res.json().get("balance", 0.0))
        except: pass
        return 0.0
