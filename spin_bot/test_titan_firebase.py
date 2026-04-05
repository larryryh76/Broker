import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from spin_bot.titan_stealth import TitanStealthClient

@pytest.mark.asyncio
async def test_firebase_handshake_restoration_payload():
    client = TitanStealthClient()

    # We must patch Playwright request context since we moved to native calls
    mock_request_context = MagicMock()
    mock_request_context.post = AsyncMock()

    mock_res = MagicMock()
    mock_res.status = 200
    mock_res.json = AsyncMock(return_value={
        "fid": "new_fid",
        "authToken": {"token": "new_token"},
        "refreshToken": "new_refresh"
    })
    mock_request_context.post.return_value = mock_res

    # Mock playwright object
    mock_pw = MagicMock()
    mock_pw.request.new_context = AsyncMock(return_value=mock_request_context)
    client.playwright = mock_pw

    # Ensure we test the registration branch
    client.load_firebase_identity = MagicMock(return_value=None)
    client.save_firebase_identity = MagicMock()

    await client._get_firebase_token()

    # Verify exact payload requirements
    mock_request_context.post.assert_called()
    args, kwargs = mock_request_context.post.call_args
    payload = kwargs['data']
    assert payload['appId'] == "1:753470331102:web:ae7465077d2fa908d70a4f"
    assert payload['authVersion'] == "FIS_v2"
    assert kwargs['headers']['x-goog-api-key'] == client.firebase_api_key

@pytest.mark.asyncio
async def test_identity_persistence_logic():
    client = TitanStealthClient()

    # Mock existing identity in DB
    existing_identity = {"fid": "old_fid", "refresh_token": "old_refresh"}
    client.load_firebase_identity = MagicMock(return_value=existing_identity)

    mock_request_context = MagicMock()
    mock_request_context.post = AsyncMock()

    mock_res = MagicMock()
    mock_res.status = 200
    mock_res.json = AsyncMock(return_value={
        "fid": "old_fid",
        "authToken": {"token": "refreshed_token"},
        "refreshToken": "refreshed_refresh"
    })
    mock_request_context.post.return_value = mock_res

    mock_pw = MagicMock()
    mock_pw.request.new_context = AsyncMock(return_value=mock_request_context)
    client.playwright = mock_pw

    await client._get_firebase_token()

    assert client.fid == "old_fid"
    assert client.refresh_token == "refreshed_refresh"

@pytest.mark.asyncio
async def test_wap_login_with_persistent_fid():
    client = TitanStealthClient()
    client.firebase_token = "token"
    client.fid = "fid_from_db"
    client.phone = "1"
    client.password = "2"

    mock_request_context = MagicMock()
    mock_request_context.post = AsyncMock()

    mock_res = MagicMock()
    mock_res.status = 200
    mock_res.json = AsyncMock(return_value={"data": {"loginToken": "session_token"}})
    mock_request_context.post.return_value = mock_res

    mock_pw = MagicMock()
    mock_pw.request.new_context = AsyncMock(return_value=mock_request_context)
    client.playwright = mock_pw

    token = await client._api_login_wap()

    assert token == "session_token"
    args, kwargs = mock_request_context.post.call_args
    assert kwargs['data']['fid'] == "fid_from_db"
