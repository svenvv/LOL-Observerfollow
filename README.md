Proof of concept!

Make sure to change the WS_url on the observer script to the address of the follower.
The follower aspect itself is working, including most interface toggles (scoreboard etc.). Toggling vision is not exposed in the render API, this would have to be sorted another way.

To make this actually suitable for use, the following 2 things still have to be implemented at least:
- error handling. -> mainly handling all things websocket.
- game state handling. League does not like having a bunch of commands sent to it while loading a game for example.
