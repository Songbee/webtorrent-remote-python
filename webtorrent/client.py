import warnings
import uuid

from eventemitter import EventEmitter


def to_camel(name):
    """
    Converts snake_case strings to camelCase.
    """
    first, *rest = name.split("_")
    return first + "".join(word.capitalize() for word in rest)


class BareRemoteTorrent:
    """
    RemoteTorrent without EventEmitter.
    """

    def __init__(self, client, key):
        self.client = client
        self.key = key
        self.server_url = None

        #: WebTorrent API, props updated once:
        self.info_hash = None
        self.name = None
        self.length = None
        self.files = []

        #: WebTorrent API, props updated with every `progress` event:
        self.progress = 0
        self.downloaded = 0
        self.uploaded = 0
        self.download_speed = 0
        self.upload_speed = 0
        self.num_peers = 0
        self.time_remaining = float("inf")

    infoHash = property(lambda self: self.info_hash)
    downloadSpeed = property(lambda self: self.download_speed)
    uploadSpeed = property(lambda self: self.upload_speed)
    numPeers = property(lambda self: self.num_peers)
    timeRemaining = property(lambda self: self.time_remaining)

    def emit(self, *a, **kw):
        return NotImplementedError("emit should be implemented")

    def create_server(self, **options):
        """
        Creates a streaming torrent-to-HTTP server. Options are passed to the
        `torrent.createServer` (optionally converted to camelCase),
        which in turn passes them to `http.createServer`.
        """

        self.client.send({
            "clientKey": self.client.client_key,
            "type": "create-server",
            "torrentKey": self.key,
            "options": {to_camel(k): v for k, v in options.items()}
        })

    createServer = create_server


class BareWebTorrentRemoteClient:
    """
    WebTorrentRemoteClient without EventEmitter or actual transport.
    """

    _remote_torrent_cls = BareRemoteTorrent

    def __init__(self):
        self.client_key = uuid.uuid4().hex[:8].upper()
        self.torrents = {}

    clientKey = property(lambda self: self.client_key)

    def emit(self, *a, **kw):
        return NotImplementedError("emit should be implemented")

    def _send(self, message):
        return NotImplementedError("_send should be implemented")

    def _receive(self, message):
        if message["clientKey"] != self.client_key:
            raise ValueError("Wrong clientKey, expected %s, got %s" %
                             (self.client_key, message["clientKey"]), message)

        if message["type"] in ["infohash", "metadata", "download",
                               "upload", "done"]:
            pass

        elif message["type"] == "server-ready":
            torrent_key = message["torrentKey"]
            self.torrents[torrent_key].server_url = message["serverURL"]

        elif message["type"] in ["error", "warning"]:
            torrent_key = message.get("torrentKey")
            if torrent_key:
                self.torrents[torrent_key].emit(message["type"],
                                                message["error"])
            else:
                self.emit(message["type"], message["error"])

        else:
            warnings.warn("Ignoring unknown message type: %r" % message)

    def add(self, torrent_id, **options):
        """
        Adds a new torrent.

        Args:
            torrent_id (str): can be one of: magnet uri, info hash, http/https
                url to a torrent file, filesystem path to a torrent file
                (if server is running on the same mactine)

        Keyword Args:
            announce (list): Torrent trackers to use (added to list in
                .torrent or magnet uri)
            max_web_conns (int): Max number of simultaneous connections
                per web seed [default=4]
            path (str): Folder to download files to (default=`/tmp/webtorrent/`)

        Returns:
            torrent object (depends on an implementation)
        """

        torrent_key = uuid.uuid4().hex[:8].upper()
        self._send({
            "clientKey": self.client_key,
            "type": "add-torrent",
            "torrentKey": torrent_key,
            "torrentID": torrent_id,
            "options": {to_camel(k): v for k, v in options.items()}
        })
        torrent = self._remote_torrent_cls(self, torrent_key)
        self.torrents[torrent_key] = torrent
        return torrent


class RemoteTorrent(EventEmitter, BareRemoteTorrent):
    """
    A proxy to the Torrent object in WebTorrent server.
    """

    pass


class BaseWebTorrentRemoteClient(EventEmitter, BareWebTorrentRemoteClient):
    """
    A proxy to the WebTorrent object in WebTorrent server.
    """

    _remote_torrent_cls = RemoteTorrent


class WebTorrentRemoteClient(BaseWebTorrentRemoteClient):
    """
    Simplest use case of WebTorrentRemoteClient.

    Listen for the `_send` event and send the message to the server process.
    When messages come back from the server, call `client.receive`.
    """

    def _send(self, message):
        self.emit("_send", message)

    def receive(self, message):
        """
        Call this when messages come back from the IPC channel.

        Args:
            message (dict): Message received from the server.
        """

        return self._receive(message)

    def on(self, event, listener=None):
        """
        Bind a listener to a particular event. Helper method that can be used
        as a decorator.

        Args:
            event (str): The name of the event to listen for. This may be any
                string value.
            listener (def or async def): The callback to execute when the event
                fires. This may be a sync or async function. If omitted,
                this function acts as a decorator.
        """

        if listener is None:
            def decorator(f):
                super().on(event, listener)
                return f
            return decorator

        return super().on(event, listener)
