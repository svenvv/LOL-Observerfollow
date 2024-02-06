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

async def post_render_data_to_replay_api(data):
    async with httpx.AsyncClient(verify=False) as client:
        await client.post("https://sven.thaus:2999/replay/render", data=data)
        if response.status_code == 200:
            print("Data sent to replay api")

async def server(websocket, path):
    async for message in websocket:
        data = json.loads(message)
        data['cameraMode'] = "fps"
        await post_render_data_to_replay_api(data)

start_server = websockets.serve(server, "0.0.0.0", 8765)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()