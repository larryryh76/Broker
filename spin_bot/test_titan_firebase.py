import pytest
import os
import json
from unittest.mock import AsyncMock, MagicMock, patch
from spin_bot.titan_stealth import TitanStealthClient

@pytest.mark.asyncio
async def test_load_storage_state_recovery():
    client = TitanStealthClient()

    # 1. Test artifact loading
    os.makedirs("artifacts", exist_ok=True)
    dummy_state = {"cookies": [], "origins": []}
    with open("artifacts/storage_state.json", "w") as f:
        json.dump(dummy_state, f)

    state = client.load_storage_state()
    assert state == dummy_state

    # Cleanup
    os.remove("artifacts/storage_state.json")

@pytest.mark.asyncio
async def test_public_handshake_payload():
    client = TitanStealthClient()
    client.playwright = MagicMock()

    mock_request_context = MagicMock()
    mock_request_context.post = AsyncMock()

    mock_res = MagicMock()
    mock_res.status = 200
    mock_res.json = AsyncMock(return_value={
        "fid": "fid",
        "authToken": {"token": "token"},
        "refreshToken": "refresh"
    })
    mock_request_context.post.return_value = mock_res
    client.playwright.request.new_context = AsyncMock(return_value=mock_request_context)

    await client._get_firebase_token()

    # Verify sdkVersion in payload
    args, kwargs = mock_request_context.post.call_args
    payload = kwargs['data']
    assert payload['sdkVersion'] == "w:10.13.0"
    assert payload['appId'] == "1:753470331102:web:ae7465077d2fa908d70a4f"

@pytest.mark.asyncio
async def test_manual_login_fallback_triggered():
    client = TitanStealthClient()
    client.setup_db = AsyncMock()
    client._api_login_wap = AsyncMock(return_value=None)
    client.load_storage_state = MagicMock(return_value=None)
    client.setup_browser = AsyncMock()
    client.manual_ui_login_fallback = AsyncMock(return_value=True)

    client.page = MagicMock()
    client.page.goto = AsyncMock()
    client.page.url = "login"
    client.page.locator.return_value.is_visible = AsyncMock(return_value=False)

    success = await client.login()

    assert success is True
    client.manual_ui_login_fallback.assert_called()
