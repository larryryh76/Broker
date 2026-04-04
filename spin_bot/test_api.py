import pytest
from spin_bot.api_client import OmniAPIClient, normalize_url

def test_normalize_url():
    assert normalize_url("https://www.football.com/api") == "https://www.football.com/api"
    assert normalize_url("//www.football.com/api") == "https://www.football.com/api"
    assert normalize_url("/api") == "https://www.football.com/api"

def test_api_client_headers():
    client = OmniAPIClient()
    assert "User-Agent" in client.session.headers
    assert "Origin" in client.session.headers
    assert client.session.headers["Origin"] == "https://www.football.com"
