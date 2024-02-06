'''	
1. connect to the websocket server
2. send the replay api data to the server
'''
import asyncio
import websockets
import httpx

ws_url = "ws://sven.thaus:8765"

async def collect_render_data():
#grab the data from the replay api using httpx
#we don't need to parse the data, just send it to the server as a string
    async with httpx.AsyncClient() as client:
        r = await client.get('https://127.0.0.1:2999/replay/render')
        data = r.text
        return data
    
async def send_data(url):
    async with websockets.connect(url) as ws:
        while True:
            data = collect_render_data()
            await ws.send(data)

# Run the send_data coroutine
asyncio.run(send_data(ws_url))