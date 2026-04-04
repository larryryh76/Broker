import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from spin_bot.titan_stealth import TitanStealthClient

@pytest.mark.asyncio
async def test_heuristic_filter():
    client = TitanStealthClient()

    # Tracker URL (should be rejected)
    tracker_url = "https://www.google-analytics.com/g/collect?v=2&tid=G-CB4CRH59G2"
    assert client._is_valid_auth_endpoint(tracker_url) is False

    # External URL (should be rejected)
    external_url = "https://www.facebook.com/login"
    assert client._is_valid_auth_endpoint(external_url) is False

    # Real Football.com Login API (should be accepted)
    valid_url = "https://www.football.com/api/ng/auth/login"
    assert client._is_valid_auth_endpoint(valid_url) is True

    # Real Football.com Sign-in (should be accepted)
    valid_url2 = "https://www.football.com/ng/m/sign-in"
    assert client._is_valid_auth_endpoint(valid_url2) is True

@pytest.mark.asyncio
async def test_interceptor_discovery_with_heuristic():
    client = TitanStealthClient()

    # Mock a tracker request
    req_tracker = MagicMock()
    req_tracker.url = "https://www.google-analytics.com/g/collect"
    req_tracker.method = "POST"
    await client._on_request(req_tracker)
    assert client.discovered_login_url is None

    # Mock a real request
    req_valid = MagicMock()
    req_valid.url = "https://www.football.com/api/ng/auth/login"
    req_valid.method = "POST"
    await client._on_request(req_valid)
    assert client.discovered_login_url == req_valid.url

@pytest.mark.asyncio
async def test_golden_ticket_immediate_save():
    client = TitanStealthClient()
    client.page = MagicMock()
    client.page.url = "https://www.football.com/ng/m/me"
    client.context = MagicMock()
    client.context.storage_state = AsyncMock(return_value={})
    client.save_storage_state = MagicMock()

    mock_frame = MagicMock()
    client.page.main_frame = mock_frame

    await client._on_framenavigated(mock_frame)
    client.save_storage_state.assert_called()
