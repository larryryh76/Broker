import pytest
from spin_bot.api_client import normalize_url, OmniAPIClient

def test_normalize_url():
    # 1. Protocol-Relative
    assert normalize_url("//example.com/api") == "https://example.com/api"

    # 2. Relative Path
    assert normalize_url("/v1/history") == "https://www.football.com/v1/history"
    assert normalize_url("v1/history") == "https://www.football.com/v1/history"

    # 3. Absolute URL with double slashes fix
    assert normalize_url("https://www.football.com//api//ng//") == "https://www.football.com/api/ng/"

    # 4. Already correct
    assert normalize_url("https://api.football.com/v2") == "https://api.football.com/v2"

def test_api_client_hydration():
    data = {
        "headers": {"X-Test": "Value"},
        "cookies": [{"name": "test_cookie", "value": "123", "domain": "football.com"}],
        "auth_state": {
            "accessToken": "secret_token",
            "puid": "user_id"
        },
        "endpoints": {
            "history": "/api/history",
            "bet": "https://bet.football.com/place"
        }
    }
    client = OmniAPIClient(session_data=data)

    # Check Headers
    assert client.headers["X-Test"] == "Value"
    assert client.headers["accessToken"] == "secret_token"
    assert client.headers["Authorization"] == "Bearer secret_token"

    # Check Endpoints (Normalized)
    assert client.endpoints["history"] == "https://www.football.com/api/history"
    assert client.endpoints["bet"] == "https://bet.football.com/place"

if __name__ == "__main__":
    pytest.main([__file__])
