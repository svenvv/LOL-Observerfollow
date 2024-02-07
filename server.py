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
import aiohttp

websocket_data = {}
old_render_data: dict = {}
remote_game_paused = True
local_game_paused = True

def create_render_data_diff(new_data) -> dict:
    global old_render_data
    update_data = new_data.copy()
    #delete cameraPosition and cameraRotation from the new data. these will be handled in the sequence endpoint
    if 'cameraPosition' in update_data:
        del update_data['cameraPosition']
    if 'cameraRotation' in update_data:
        del update_data['cameraRotation']
    #remove all the keys from the new data that are same as old data
    for key in old_render_data:
        if key in update_data and old_render_data[key] == update_data[key]:
            del update_data[key]
    old_render_data = update_data
    return update_data

sequence_position: list = []
sequence_rotation: list = []
sequence_speed: list = []
SEQUENCE_LEN = 25
async def sequence_handler(render: dict, playback:dict) -> dict:
    global sequence_position
    global sequence_rotation
    global sequence_speed
    #the lists hold the last 5 values for the respective keys.
    #these values are all sent to the sequence endpoint of the local replay api
    #the sequence endpoint will interpolate between these values to create a smooth transition
    #old values are removed from the dictionary when a new value is added.
    #when going back in time, the sequence is cleared and only the new data is sent to the sequence endpoint. the new time will also be sent to the playback endpoint
    if len(sequence_speed) > 0:
        #if the new time is less than the last time in the sequence, clear all sequences and start over
        if 'time' in playback and playback['time'] < sequence_speed[-1]['time']:
            sequence_position = []
            sequence_rotation = []
            sequence_speed = []
            async with aiohttp.ClientSession() as session:
                async with session.post('https://127.0.0.1:2999/replay/sequence', data="{}", ssl=False, headers={'Content-Type': 'application/json'}) as resp:
                    pass
            print('clearing sequence')
            
    if 'cameraPosition' in render:
        sequence_position.append(render['cameraPosition'])
        if len(sequence_position) > SEQUENCE_LEN:
            sequence_position.pop(0)
    else:
        raise ValueError('cameraPosition not in render data')

    if 'cameraRotation' in render:
        sequence_rotation.append(render['cameraRotation'])
        if len(sequence_rotation) > SEQUENCE_LEN:
            sequence_rotation.pop(0)
    else:
        raise ValueError('cameraRotation not in render data')

    if 'time' in playback:
        sequence_speed.append(playback)
        if len(sequence_speed) > SEQUENCE_LEN:
            sequence_speed.pop(0)
    else:
        raise ValueError('time not in playback data')

    #determine the blend type to use for the position sequence
    #linear is default, but we need to use snap if the difference between the last and current position is too large
    if len(sequence_position) < 2:
        position_blend = 'snap'
    else:
        last_x_pos = sequence_position[-2]['x']
        last_z_pos = sequence_position[-2]['z']
        current_x_pos = sequence_position[-1]['x']
        current_z_pos = sequence_position[-1]['z']
        if abs(current_x_pos - last_x_pos) < 200 or abs(current_z_pos - last_z_pos) < 200:
            position_blend = 'linear'
        else:
            position_blend = 'snap'
            #set the time to be like 1 microsecond after the previous time. this will make the sequence endpoint actually snap instead of doing some weird interpolation
            sequence_speed[-1]['time'] = sequence_speed[-2]['time'] + 0.000001

    #create the json object to send to the sequence endpoint
    position_data: list = []
    for i, position in enumerate(sequence_position):
        position_data.append({
            "blend": position_blend,
            "time": sequence_speed[i]['time'],
            "value": position
        })
    rotation_data: list = []
    for i, rotation in enumerate(sequence_rotation):
        rotation_data.append({
            "blend": "linear",
            "time": sequence_speed[i]['time'],
            "value": rotation
        })
    speed_data: list = []
    for speed in sequence_speed:
        speed_data.append({
            "blend": "linear",
            "time": speed['time'],
            "value": speed['speed']
        })

    return {
        "cameraPosition": position_data,
        "cameraRotation": rotation_data,
        "playbackSpeed": speed_data
    } 

   
async def server(websocket, path):
    global websocket_data
    async for message in websocket:
        websocket_data = json.loads(message)


async def data_loop():
    global websocket_data
    global remote_game_paused, local_game_paused
    global sequence_rotation, sequence_position, sequence_speed
    old_websocket_data = {} 
    while True:
        await asyncio.sleep(0.01)
        if websocket_data != old_websocket_data and len(websocket_data) > 0:
            old_websocket_data = websocket_data.copy()
            new_websocket_data = websocket_data.copy()

            render_data = new_websocket_data['render']
            playback_data = new_websocket_data['playback']

            if 'cameraAttached' in render_data:
                render_data['cameraAttached'] = False
            if 'cameraMode' in render_data:
                render_data['cameraMode'] = 'fps'

            sequence_data = await sequence_handler(render_data, playback_data)
            if len(sequence_data['cameraPosition']) == SEQUENCE_LEN-1:
                async with aiohttp.ClientSession() as session:                                                                                        
                        async with session.post('https://127.0.0.1:2999/replay/playback', data=json.dumps(sequence_data['playbackSpeed'][int(SEQUENCE_LEN/4)]), ssl=False, headers={'Content-Type': 'application/json'}) as resp:
                            pass
            async with aiohttp.ClientSession() as session:
                async with session.post('https://127.0.0.1:2999/replay/sequence', data=json.dumps(sequence_data), ssl=False, headers={'Content-Type': 'application/json'}) as resp:
                    pass
                
            #fire a post request to the local replay api. we don't care about the response. return immediately so we can get the next message from the client
            #TODO - delay by the same number of messages as SEQUENCE_LEN
            render_diff = create_render_data_diff(render_data)
            if len(render_diff) > 0:
                async with aiohttp.ClientSession() as session:
                    async with session.post('https://127.0.0.1:2999/replay/render', data=json.dumps(render_diff), ssl=False, headers={'Content-Type': 'application/json'}) as resp:
                        pass

            #if an observer (un)pauses the game, we need to (un)pause the game in the local replay api as well.
            if "paused" in playback_data:
                remote_game_paused = playback_data['paused']
                if local_game_paused != remote_game_paused:
                    sequence_rotation = []
                    sequence_position = []
                    sequence_speed = []
                    print(f'clearing sequence. remote paused: {remote_game_paused}, local paused: {local_game_paused}')
                    async with aiohttp.ClientSession() as session:
                        async with session.post('https://127.0.0.1:2999/replay/playback', data=json.dumps({"paused": remote_game_paused}), ssl=False, headers={'Content-Type': 'application/json'}) as resp:
                            pass
                        async with session.post('https://127.0.0.1:2999/replay/sequence', data="{}", ssl=False, headers={'Content-Type': 'application/json'}) as resp:
                            pass

async def local_gamestate_loop():
    global local_game_paused
    global sequence_speed, sequence_rotation, sequence_position
    while True:
        await asyncio.sleep(0.1)
        async with aiohttp.ClientSession() as session:
            async with session.get('https://127.0.0.1:2999/replay/playback', ssl=False) as resp:
                data = await resp.json()
                if 'paused' in data and 'seeking' in data:
                    if not data['seeking']:
                        local_game_paused = data['paused']
                        if 'time' in data:
                            #if the time differs by more than 1 seconds, we need to clear the sequence
                            if len(sequence_speed) == SEQUENCE_LEN and abs(sequence_speed[0]['time'] - data['time']) > 0.5:
                                print(f'clearing sequence. old time: {sequence_speed[0]["time"]}, new time: {data["time"]}')
                                sequence_rotation = []
                                sequence_position = []
                                sequence_speed = []
                                #clear the sequence in the local replay api
                                async with session.post('https://127.0.0.1:2999/replay/sequence', data="{}", ssl=False, headers={'Content-Type': 'application/json'}) as resp:
                                    pass


start_server = websockets.serve(server, "0.0.0.0", 8765)

asyncio.get_event_loop().create_task(data_loop())
asyncio.get_event_loop().create_task(local_gamestate_loop())
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
