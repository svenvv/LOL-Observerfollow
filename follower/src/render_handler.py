'''
This file handles the updating of render data
'''

import asyncio
import logging
import aiohttp
import json

class RenderHandler:
    def __init__(self, sequence_len, sequence_divider):
        self._last_render_data = {}
        self._last_local_render_data_lock = asyncio.Lock()
        self.render_sequence: list[dict] = []
        self.sequence_len = sequence_len
        self.sequence_divider = sequence_divider
        self.diff_data_position = int(sequence_len/sequence_divider)

    def sanitize_render_data(self, data:dict, modify=True, delete=True) -> dict:
        '''
        Sanitize the render data
        data: dict: the render data
        modify: bool: Modify the attached camera and camera mode
        delete: bool: Delete the camera position and rotation
        '''
        if modify:
            if 'cameraAttached' in data:
                data['cameraAttached'] = False
            if 'cameraMode' in data:
                data['cameraMode'] = 'fps'
        if delete:
            if 'cameraPosition' in data:
                del data['cameraPosition']
            if 'cameraRotation' in data:
                del data['cameraRotation']
        return data

    def add_to_render_sequence(self, data:dict):
        '''
        Add data to the render sequence
        '''
        data = self.sanitize_render_data(data.copy(), modify=True, delete=True)
        self.render_sequence.append(data)
        if len(self.render_sequence) > self.sequence_len:
            self.render_sequence.pop(0)
          
    async def post_render_sequence(self, data:dict):
        '''
        Post the render sequence
        '''
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post('https://127.0.0.1:2999/replay/render', ssl=False, data=json.dumps(data), headers={'Content-Type': 'application/json'}) as resp:
                    pass
        except Exception as e:
            logging.error(f"error posting render data: {e}")

    def create_render_data_diff(self) -> dict:
        if len(self.render_sequence) == 0:
            return {}
        #if the sequence is not full, return the last render data
        if len (self.render_sequence) < self.sequence_len:
            return self.render_sequence[-1]

        diff_data = self.render_sequence[self.diff_data_position].copy()
        old_data = self.render_sequence[self.diff_data_position-1]
        
        #remove all the keys from the new data that are same as old data
        for key in old_data:
            if key in diff_data and old_data[key] == diff_data[key]:
                del diff_data[key]
        old_data = diff_data
        return diff_data
    

    async def local_render_data_loop(self):
        '''
        Update the local render data using an asyncio loop every 0.5 seconds
        every second, check if the render sequence is full and post the last render data to the local replay api if it is different.
        '''
        while True:
            count = 0
            await asyncio.sleep(0.5)
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get('https://127.0.0.1:2999/replay/render', ssl=False) as resp:
                        data = await resp.json()
                        self.last_local_render_data = data
                        count += 1
                        if count > 1 and len(self.render_sequence) == self.sequence_len:
                            if self.sanitize_render_data(data, modify=False) != self.render_sequence[-1]:
                                await self.post_render_sequence(self.render_sequence[-1])
                                count = 0
            except Exception as e:
                logging.error(f"error getting local render data: {e}")

    @property
    async def last_local_data(self):
        '''
        Get the last render data
        '''
        async with self._last_local_render_data_lock:
            if type(self.last_local_render_data) == dict:
                return self.last_local_render_data.copy()
            return self.last_local_render_data
        
    @last_local_data.setter
    async def last_local_data(self, data):
        '''
        Set the last render data
        '''
        async with self._last_local_render_data_lock:
            self.last_local_render_data = data