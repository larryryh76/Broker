import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from spin_bot.titan_stealth import TitanStealthClient

@pytest.mark.asyncio
async def test_header_sync_payload():
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

    # Verify Sync Headers
    args, kwargs = mock_request_context.post.call_args
    headers = kwargs['headers']
    assert headers['Origin'] == "https://www.football.com"
    assert headers['Referer'] == "https://www.football.com/"

@pytest.mark.asyncio
async def test_manual_login_direct_route():
    client = TitanStealthClient()
    client.setup_db = AsyncMock()
    client._api_login_wap = AsyncMock(return_value=None)
    client.load_storage_state = MagicMock(return_value=None)
    client.setup_browser = AsyncMock()
    client.manual_ui_login_fallback = AsyncMock(return_value=True)

    client.page = MagicMock()
    client.page.goto = AsyncMock()
    client.page.url = "index"
    client.page.locator.return_value.is_visible = AsyncMock(return_value=False)

    await client.login()

    # Verify direct route for fallback
    client.manual_ui_login_fallback.assert_called()
