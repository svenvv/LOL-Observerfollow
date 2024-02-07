'''
This file handles the updating of sequence data
'''

import logging
import aiohttp
import json

class SequenceHandler:
    def __init__(self, sequence_len, sequence_divider):
        self.sequence_position: list[dict] = []
        self.sequence_rotation: list[dict] = []
        self.sequence_speed: list[dict] = []
        self.sequence_len = sequence_len
        self.sequence_divider = sequence_divider
        self.diff_data_position = int(sequence_len/sequence_divider)

    async def post_replay_sequence(self, data: dict):
        '''
        Post the replay sequence
        '''
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post('https://127.0.0.1:2999/replay/sequence', data=json.dumps(data), ssl=False, headers={'Content-Type': 'application/json'}) as resp:
                    pass
        except Exception as e:
            logging.error(f"error posting replay sequence: {e}")

    async def clear_sequence(self):
        '''
        Clear the sequence
        '''
        self.sequence_position = []
        self.sequence_rotation = []
        self.sequence_speed = []
        await self.post_replay_sequence({})
        logging.info('Cleared sequence')

    async def add_to_sequence(self, render: dict, playback: dict) -> int:
        '''
        Add data to the sequence
        return: int: the length of the sequence
        '''
        if len(self.sequence_speed) > 0:
            #if the new time is less than the last time in the sequence, clear all sequences and start over
            if 'time' in playback and playback['time'] < self.sequence_speed[-1]['time']:
                logging.warning('New time is less than last time in sequence. Clearing sequence')
                await self.clear_sequence()
                
        if 'cameraPosition' in render and 'cameraRotation' in render and 'time' in playback:
            self.sequence_position.append(render['cameraPosition'])
            if len(self.sequence_position) > self.sequence_len:
                self.sequence_position.pop(0)

            self.sequence_rotation.append(render['cameraRotation'])
            if len(self.sequence_rotation) > self.sequence_len:
                self.sequence_rotation.pop(0)

            self.sequence_speed.append(playback)
            if len(self.sequence_speed) > self.sequence_len:
                self.sequence_speed.pop(0)

            return len(self.sequence_speed)
        else:
            logging.error('cameraPosition, cameraRotation, or time not in render or playback data')
            return 0
        
    def position_blend_type(self, max_deviation: int) -> str:
        #determine the blend type to use for the position sequence
        #linear is default, but we need to use snap if the difference between the last and current position is too large
        if len(self.sequence_position) < 2:
            position_blend = 'snap'
        else:
            last_x_pos = self.sequence_position[-2]['x']
            last_z_pos = self.sequence_position[-2]['z']
            current_x_pos = self.sequence_position[-1]['x']
            current_z_pos = self.sequence_position[-1]['z']
            if abs(current_x_pos - last_x_pos) < max_deviation or abs(current_z_pos - last_z_pos) < max_deviation:
                position_blend = 'linear'
            else:
                position_blend = 'snap'
                #set the time to be like 1 microsecond after the previous time. this will make the sequence endpoint actually snap instead of doing some weird interpolation
                self.sequence_speed[-1]['time'] = self.sequence_speed[-2]['time'] + 0.000001
        return position_blend

    def create_replay_sequence(self) -> dict:
        #create the json object to send to the sequence endpoint
        position_data: list = []
        for i, position in enumerate(self.sequence_position):
            position_data.append({
                "blend": self.position_blend_type(150),
                "time": self.sequence_speed[i]['time'],
                "value": position
            })
        rotation_data: list = []
        for i, rotation in enumerate(self.sequence_rotation):
            rotation_data.append({
                "blend": "linear",
                "time": self.sequence_speed[i]['time'],
                "value": rotation
            })
        speed_data: list = []
        for speed in self.sequence_speed:
            speed_data.append({
                "blend": "linear",
                "time": speed['time'],
                "value": speed['speed']
            })

        logging.debug(f"Position data: {position_data}")
        logging.debug(f"Rotation data: {rotation_data}")
        logging.debug(f"Speed data: {speed_data}")
        return {
            "cameraPosition": position_data,
            "cameraRotation": rotation_data,
            "playbackSpeed": speed_data
        }