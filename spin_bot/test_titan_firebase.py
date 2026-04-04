import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from spin_bot.titan_stealth import TitanStealthClient

@pytest.mark.asyncio
async def test_firebase_handshake_and_api_login():
    client = TitanStealthClient()
    client.phone = "123"
    client.password = "456"

    with patch('requests.post') as mock_post:
        # 1. Mock Handshake Response
        mock_handshake = MagicMock()
        mock_handshake.status_code = 200
        mock_handshake.json.return_value = {
            "fid": "test_fid",
            "authToken": {"token": "test_token"}
        }

        # 2. Mock Login Response
        mock_login = MagicMock()
        mock_login.status_code = 200
        mock_login.json.return_value = {
            "data": {"loginToken": "test_login_token"}
        }

        mock_post.side_effect = [mock_handshake, mock_login]

        token = await client._api_login_wap()
        assert token == "test_login_token"
        assert client.fid == "test_fid"

@pytest.mark.asyncio
async def test_ui_sensitivity_suite_injection():
    client = TitanStealthClient()
    client.page = AsyncMock()

    await client._apply_ui_sensitivity()

    client.page.add_init_script.assert_called()
    script = client.page.add_init_script.call_args[0][0]
    assert "preconnect" in script
    assert "Asset Retry" in script
    assert "applyThemeStyle" in script
    assert "triggerLoginModal" in script
    assert "zIndex" in script

@pytest.mark.asyncio
async def test_vue_hydration_wait():
    client = TitanStealthClient()
    client.page = AsyncMock()

    await client.wait_for_vue_hydration()

    client.page.wait_for_response.assert_called()
    predicate = client.page.wait_for_response.call_args[0][0]

    mock_res = MagicMock()
    mock_res.url = "https://www.football.com/api/ng/factsCenter/recommend/configs"
    assert predicate(mock_res) is True
