'''
This file contains the code for the websocket server that will be used to communicate with the observer.
also contains any error handling and reconnecting logic for the websocket server.
'''
import websockets
import json
import logging
import asyncio

class WebsocketServer:
    def __init__(self, port):
        self._last_data = {}
        self._last_data_lock = asyncio.Lock()
        self.port = port

    async def start_server(self):
        '''
        Start the websocket server and listen for incoming messages
        '''
        try:
            async with websockets.serve(self.handler, "0.0.0.0", self.port):
                await asyncio.Future()  # run forever
        except Exception as e:
            logging.error(f"Error starting server: {e}")
            await asyncio.sleep(5)
            await self.start_server()

    async def handler(self, websocket, path):
        '''
        Handle incoming messages from the observer
        '''
        async for message in websocket:
            await self.handle_message(message)
    
    async def handle_message(self, message: str):
        '''
        Handle incoming messages from the observer
        '''
        try:
            data = json.loads(message)
            logging.debug(f"Received message: {data}")
            async with self._last_data_lock:
                self._last_data = data
        except Exception as e:
            logging.error(f"Error handling message: {e}")

    @property
    async def last_data(self):
        '''
        Get the last data received from the observer
        '''
        async with self._last_data_lock:
            if type(self._last_data) == dict:
                return self._last_data.copy()
            return self._last_data