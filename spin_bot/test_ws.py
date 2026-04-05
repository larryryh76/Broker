import asyncio
import os
import socketio
from spin_bot.titan_stealth import TitanStealthClient

async def test_websocket_handshake():
    client = TitanStealthClient()
    print("Testing ALIVE-NG WebSocket Handshake (Direct WebSocket)...")

    sio = socketio.AsyncClient(logger=True, engineio_logger=True)

    @sio.event
    async def connect():
        print("CONNECTED")

    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 14; CPH2641) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.119 Mobile Safari/537.36",
        "Origin": "https://www.football.com",
        "Referer": "https://www.football.com/"
    }

    try:
        # Exact URL from instructions
        # Note: transport=websocket means we should skip polling
        url = "wss://alive-ng.football.com/socket.io/?EIO=3&transport=websocket"
        await sio.connect(
            url,
            transports=['websocket'],
            headers=headers
        )
        print("SUCCESS")
    except Exception as e:
        print(f"FAILED: {e}")

    if sio.connected:
        await sio.disconnect()

if __name__ == "__main__":
    asyncio.run(test_websocket_handshake())
