# League of Legends Observer Follow

This is a proof of concept for a follower script for the League of Legends Replay Client. Similar to Valorants own Observer Follow feature, this script allows to automatically copy the camera movements and interface toggles of an observer to another League of Legends Game client.

### Disclaimer!

This is a proof of concept and not a finished product. It is not suitable for use in a production environment.

To make this actually suitable for use, the following 2 things still have to be implemented at least:

- error handling. -> mainly handling all things websocket.
- game state handling. League does not like having a bunch of commands sent to it while loading a game for example.

## Installation

1. Install [Python 3.10+](https://www.python.org/downloads/)
2. Optional: Use a [virtual environment](https://docs.python.org/3/library/venv.html#creating-virtual-environments)
3. Install the required packages with `pip install -r requirements.txt`

## Usage

### Follower PC

1. Forward port `8765`, or change the port number in `follwer/main.py` to the forwarded port of your choice.
2. Enable the [Replay API](https://developer.riotgames.com/docs/lol#game-client-api_replay-api) for your game client.
3. Start League of Legends and open a replay. Make sure the Follower and Observer are in the same game.
4. Once the game has started, run `python follower/main.py` to start the follower.

Your Follower PC will now copy the camera movements and interface toggles of the Observer PC.

### Observer PC

1. Change the `WS_URL` in `observer/main.py` to the address of the follower. It should look like `ws://<FOLLOWER_IP>:<PORT>`.
2. Enable the [Replay API](https://developer.riotgames.com/docs/lol#game-client-api_replay-api) for your game client.
3. Start League of Legends and open a replay. Make sure the Follower and Observer are in the same game.
4. Once the game has started, run `python observer/main.py` to start the observer.

Your Observer PC will now send the camera movements and interface toggles to the Follower PC.
