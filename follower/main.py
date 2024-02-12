'''	
1. setup websocket server
2. get the replay api data from the client.
   - playback
   - render
3. change camera mode to fps and attached to false
4. send data to local replay api
'''
import asyncio
import json
import aiohttp
import logging
import time

from src.websocket_server import WebsocketServer
from src.render_handler import RenderHandler
from src.sequence_handler import SequenceHandler

SEQUENCE_LEN = 25
SEQUENCE_DIVIDER = 4
MAX_TIME_DIFF = 0.5

websocket_server = WebsocketServer(8765)
render_handler = RenderHandler(SEQUENCE_LEN, SEQUENCE_DIVIDER)
sequence_handler = SequenceHandler(SEQUENCE_LEN, SEQUENCE_DIVIDER)
local_game_paused = True
local_playback_state: dict = {}

async def post_playback_data(data: dict):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post('https://127.0.0.1:2999/replay/playback', data=json.dumps(data), ssl=False, headers={'Content-Type': 'application/json'}) as resp:
                pass
    except Exception as e:
        logging.error(f"error posting playback data: {e}")


async def handle_render_data(data: dict):
    global render_handler
    render_handler.add_to_render_sequence(data)
    # create a diff of the render data in the sequence at the same position the local replay api should be at (SEQUENCE_LEN/SEQUENCE_DIVIDER)
    diff = render_handler.create_render_data_diff()
    if len(diff) > 0:  # something changed
        logging.info(f"Sending render diff: {diff}")
        await render_handler.post_render_sequence(diff)

sync_timeout: float = 0


async def handle_sequence_data(render_data: dict, playback_data: dict):
    global sequence_handler, sync_timeout
    seq_len = await sequence_handler.add_to_sequence(render_data, playback_data)
    replay_sequence = sequence_handler.create_replay_sequence()
    if seq_len == SEQUENCE_LEN - 1:
        logging.info(f"Setting time: {replay_sequence['playbackSpeed'][int(
            SEQUENCE_LEN/SEQUENCE_DIVIDER)]['time']}")
        await post_playback_data(replay_sequence['playbackSpeed'][int(SEQUENCE_LEN/SEQUENCE_DIVIDER)])
    if seq_len == SEQUENCE_LEN:
        # check if the time is different by more than MAX_TIME_DIFF seconds
        if abs(local_playback_state['time'] - replay_sequence['playbackSpeed'][int(SEQUENCE_LEN/SEQUENCE_DIVIDER)]['time']) > MAX_TIME_DIFF and time.time() > sync_timeout and not local_playback_state['seeking']:
            logging.warning(f"Out of sync! resetting time: {
                            replay_sequence['playbackSpeed'][int(SEQUENCE_LEN/SEQUENCE_DIVIDER)]['time']}")
            await post_playback_data(replay_sequence['playbackSpeed'][int(SEQUENCE_LEN/SEQUENCE_DIVIDER)])
            sync_timeout = time.time() + 5

    await sequence_handler.post_replay_sequence(replay_sequence)


async def handle_playback_data(data: dict):
    global local_game_paused
    if 'paused' in data:
        remote_game_paused = data['paused']
        if local_game_paused != remote_game_paused:
            logging.info(f"Setting paused: {remote_game_paused}")
            await post_playback_data({"paused": remote_game_paused})
            await sequence_handler.clear_sequence()
            # the local gamestate loop will overwrite this again if it's different
            local_game_paused = remote_game_paused


async def data_loop():
    global websocket_server
    old_websocket_data = {}
    while True:
        await asyncio.sleep(0.01)
        websocket_data = await websocket_server.last_data
        if websocket_data != old_websocket_data and len(websocket_data) > 0:
            old_websocket_data = websocket_data.copy()

            render_data = websocket_data['render']
            playback_data = websocket_data['playback']

            await handle_render_data(render_data)
            await handle_sequence_data(render_data, playback_data)
            await handle_playback_data(playback_data)


async def local_gamestate_loop():
    global local_game_paused, local_playback_state
    while True:
        await asyncio.sleep(0.1)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('https://127.0.0.1:2999/replay/playback', ssl=False) as resp:
                    data = await resp.json()
                    # when the game is seeking it means that the observer is going forward or backward in time. Paused will always be true when seeking, even if the observer hasn't paused the game.
                    if 'paused' in data and 'seeking' and 'time' in data:
                        local_playback_state = data
                        if not data['seeking']:
                            local_game_paused = data['paused']
        except Exception as e:
            logging.error(f"error getting local gamestate: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logging.info("Starting follower")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    asyncio.get_event_loop().create_task(data_loop())
    asyncio.get_event_loop().create_task(local_gamestate_loop())
    asyncio.get_event_loop().create_task(render_handler.local_render_data_loop())
    asyncio.get_event_loop().run_until_complete(websocket_server.start_server())
    asyncio.get_event_loop().run_forever()