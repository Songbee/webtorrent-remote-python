# webtorrent-remote-python
Control [webtorrent-remote](https://github.com/dcposch/webtorrent-remote) process from Python.

```py
from webtorrent.client import WebTorrentRemoteClient

client = WebTorrentRemoteClient()

@client.on("_send")
def send_msg_to_server(message):
    # Send `message` to the server. It's JSON serializable.
    # Use TCP, some kind of ICP, whatever.

# When messages come back from the server, call:
client.receive(message)


# Now `client` works just like a normal WebTorrent object!
torrent = client.add('magnet:?xt=urn:btih:6a9759bffd5c0af65319979fb7832189f4f3c35d')

@torrent.on("metadata")
def on_metadata():
    print(torrent.files) # [{'name': 'sintel.mp4'}]

torrent.create_server()  # or torrent.createServer()

@torrent.on("server-ready")
def on_server_ready():
    print(torrent.server_url)  # or torrent.serverURL
```
