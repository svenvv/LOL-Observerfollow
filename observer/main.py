'''	
1. connect to the websocket server
2. send the replay api data to the server
'''
import asyncio
import websockets
import httpx #TODO: replace with aiohttp
import json

WS_URL = "ws://change.me:8765"

async def collect_render_data():
#grab the data from the replay api using httpx
    try:
        async with httpx.AsyncClient(verify=False) as client:
            r = await client.get('https://127.0.0.1:2999/replay/render')
            data = r.json()
            return data
    except httpx.HTTPError as exc:
        print (f"can't connect to the replay api: {exc} retrying...")
        await collect_render_data()
    
async def collect_playback_data():
#grab the data from the replay api using httpx
    try:
        async with httpx.AsyncClient(verify=False) as client:
            r = await client.get('https://127.0.0.1:2999/replay/playback')
            data = r.json()
            return data
    except httpx.HTTPError as exc:
        print (f"can't connect to the replay api: {exc} retrying...")
        await collect_playback_data()
    
async def send_data(url):
    while True:
        try:
            async with websockets.connect(url) as ws:
                while True:
                    await asyncio.sleep(0.01)
                    render = await collect_render_data()
                    playback = await collect_playback_data()
                    data = json.dumps({"render": render, "playback": playback})
                    await ws.send(data)
        except websockets.exceptions.ConnectionClosed:
            print("Connection closed. Reconnecting...")
            await asyncio.sleep(1)  # Wait for 1 second before reconnecting

# Run the send_data coroutine
asyncio.run(send_data(WS_URL))