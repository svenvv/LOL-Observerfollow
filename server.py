'''	
1. setup websocket server
2. get the replay api data from the client.
   - playback
   - render
3. change camera mode to fps and attached to false
4. send data to local replay api
'''
import asyncio
import websockets
import json
import httpx
import mypy

async def server(websocket, path):
    async for message in websocket:
        data = json.loads(message)
        print(f"Received message: {data}")

start_server = websockets.serve(server, "0.0.0.0", 8765)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()