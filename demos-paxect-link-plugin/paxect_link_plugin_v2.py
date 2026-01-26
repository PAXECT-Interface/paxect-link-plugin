#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
PAXECT Link Plugin v2.1 — Multi-Bridge Autonomous Relay + Wormhole Discovery
=============================================================================

Upgrade van v2.0 met:
- Magic Wormhole-stijl discovery (korte codes)
- Rendezvous server (self-hostable)
- NAT traversal via relay
- Simpele CLI: --share / --connect <code>

Environment variables (nieuw):
------------------------------
PAXECT_LINK_RENDEZVOUS    Rendezvous server URL (default: lokaal bestand)
PAXECT_LINK_RELAY         Relay server voor NAT traversal

Gebruik:
--------
# Node A deelt:
python3 paxect_link_plugin_v2.py --share
→ Code: 7-tiger-mountain

# Node B verbindt:
python3 paxect_link_plugin_v2.py --connect 7-tiger-mountain

Dependencies: None (stdlib only)
"""

from __future__ import annotations
import os, sys, json, time, uuid, socket, struct, hashlib, hmac
import threading, signal, platform, subprocess, base64, secrets
import argparse, random, string
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Optional, Callable, Dict, List, Set, Tuple
from enum import Enum, auto
from collections import defaultdict
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import urlopen, Request
from urllib.error import URLError
import ssl

# ============================================================================
# CONFIGURATION
# ============================================================================

VERSION = "2.1.0"
PROTOCOL_VERSION = 2

# Existing v1.x env vars (backwards compatible)
INBOX      = Path(os.environ.get("PAXECT_LINK_INBOX", "inbox"))
OUTBOX     = Path(os.environ.get("PAXECT_LINK_OUTBOX", "outbox"))
CONFIG     = Path(os.environ.get("PAXECT_LINK_POLICY", "link_policy.json"))
MANIFEST   = Path(os.environ.get("PAXECT_LINK_MANIFEST", "link_manifest.json"))
LOGFILE    = Path(os.environ.get("PAXECT_LINK_LOG", "paxect_link_log.jsonl"))
LOCKFILE   = Path(os.environ.get("PAXECT_LINK_LOCK", ".paxect_link.lock"))
PAXECT_CORE = os.environ.get("PAXECT_CORE", "python3 paxect_core.py").split()
POLL_INTERVAL = float(os.environ.get("PAXECT_LINK_POLL_SEC", "2.0"))
BACKOFF_SEC = float(os.environ.get("PAXECT_LINK_BACKOFF_SEC", "5.0"))
LOG_MAX_BYTES = int(os.environ.get("PAXECT_LINK_LOG_MAX", str(5 * 1024 * 1024)))
HMAC_KEY = os.environ.get("PAXECT_LINK_HMAC_KEY", "")
HMAC_KEY_BYTES = HMAC_KEY.encode("utf-8") if HMAC_KEY else None

# New v2.0 env vars
SHARED_DIR = Path(os.environ.get("PAXECT_LINK_SHARED_DIR", "/tmp/paxect_shared"))
SOCKET_PORT = int(os.environ.get("PAXECT_LINK_SOCKET_PORT", "0"))
SOCKET_HOST = os.environ.get("PAXECT_LINK_SOCKET_HOST", "0.0.0.0")
IDENTITY_FILE = Path(os.environ.get("PAXECT_LINK_IDENTITY", ".paxect_node_id.json"))

# AEAD encryption (optional)
PAXECT_AEAD = os.environ.get("PAXECT_AEAD", "").split() or None
PAXECT_AEAD_PASS = os.environ.get("PAXECT_AEAD_PASS", "")
PAXECT_AEAD_PASS_FILE = os.environ.get("PAXECT_AEAD_PASS_FILE", "")

# Wormhole-style discovery (v2.1)
RENDEZVOUS_URL = os.environ.get("PAXECT_LINK_RENDEZVOUS", "")  # HTTP URL or empty for local file
RENDEZVOUS_FILE = Path(os.environ.get("PAXECT_LINK_RENDEZVOUS_FILE", "/tmp/paxect_rendezvous.json"))
RELAY_HOST = os.environ.get("PAXECT_LINK_RELAY_HOST", "")
RELAY_PORT = int(os.environ.get("PAXECT_LINK_RELAY_PORT", "9877"))
CODE_EXPIRY_SEC = int(os.environ.get("PAXECT_LINK_CODE_EXPIRY", "300"))  # 5 min default

# Word lists voor menselijke codes (Magic Wormhole stijl)
WORDLIST_ADJ = ["red", "blue", "green", "fast", "slow", "big", "small", "hot", "cold", "old",
                "new", "dark", "bright", "soft", "hard", "sweet", "sour", "wild", "calm", "bold"]
WORDLIST_NOUN = ["tiger", "eagle", "wolf", "bear", "lion", "hawk", "fox", "deer", "owl", "snake",
                 "mountain", "river", "forest", "ocean", "desert", "valley", "island", "canyon", "lake", "cave"]

# Timing
HEARTBEAT_SEC = 5.0
HEARTBEAT_TIMEOUT = 15.0
ROUTE_EXPIRE_SEC = 60.0
MAX_TTL = 16
MAX_HOPS = 32

# Default policy (v1.x compatible)
DEFAULT_POLICY = {
    "version": VERSION,
    "trusted_nodes": ["localhost"],
    "allowed_suffixes": [".bin", ".txt", ".json", ".csv", ".aead", ".freq", ".aead.freq"],
    "max_file_mb": 256,
    "require_sig": False,
    "auto_delete": True,
    "log_level": "info",
    # v2.0 additions
    "enable_socket": False,
    "enable_routing": True,
    "enable_aead": False,  # set True to require AEAD
}

_running = True

# ============================================================================
# OS ABSTRACTION LAYER
# ============================================================================

class OSLayer:
    """Cross-platform abstraction."""
    system = platform.system()
    node_name = platform.node() or "localhost"
    is_windows = system == "Windows"
    
    @staticmethod
    def atomic_write(path: Path, data: bytes):
        tmp = path.with_suffix(path.suffix + ".tmp")
        try:
            with tmp.open("wb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            tmp.replace(path)
        except Exception:
            tmp.unlink(missing_ok=True)
            raise
    
    @staticmethod
    def get_local_ip() -> str:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

# ============================================================================
# WORMHOLE-STYLE DISCOVERY
# ============================================================================

def generate_wormhole_code() -> str:
    """Genereer menselijke code: nummer-bijvoeglijk-zelfstandig."""
    num = random.randint(1, 999)
    adj = random.choice(WORDLIST_ADJ)
    noun = random.choice(WORDLIST_NOUN)
    return f"{num}-{adj}-{noun}"

def generate_short_code(length: int = 6) -> str:
    """Genereer korte alfanumerieke code."""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

@dataclass
class WormholeCode:
    """Wormhole code met connection info."""
    code: str
    node_id: str
    hostname: str
    public_key: str
    socket_addr: Optional[Tuple[str, int]] = None  # (ip, port)
    created_at: float = 0.0
    expires_at: float = 0.0
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = time.time()
        if not self.expires_at:
            self.expires_at = self.created_at + CODE_EXPIRY_SEC
    
    def is_expired(self) -> bool:
        return time.time() > self.expires_at
    
    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "node_id": self.node_id,
            "hostname": self.hostname,
            "public_key": self.public_key,
            "socket_addr": list(self.socket_addr) if self.socket_addr else None,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
        }
    
    @classmethod
    def from_dict(cls, d: dict) -> "WormholeCode":
        return cls(
            code=d["code"],
            node_id=d["node_id"],
            hostname=d["hostname"],
            public_key=d.get("public_key", ""),
            socket_addr=tuple(d["socket_addr"]) if d.get("socket_addr") else None,
            created_at=d.get("created_at", 0),
            expires_at=d.get("expires_at", 0),
        )

class RendezvousClient:
    """Client voor rendezvous server (file-based of HTTP)."""
    
    def __init__(self, url: str = "", file_path: Path = RENDEZVOUS_FILE):
        self.url = url
        self.file_path = file_path
        self._lock = threading.Lock()
    
    def publish(self, wc: WormholeCode) -> bool:
        """Publiceer code naar rendezvous."""
        if self.url:
            return self._publish_http(wc)
        return self._publish_file(wc)
    
    def lookup(self, code: str) -> Optional[WormholeCode]:
        """Zoek code op bij rendezvous."""
        if self.url:
            return self._lookup_http(code)
        return self._lookup_file(code)
    
    def remove(self, code: str) -> bool:
        """Verwijder code van rendezvous."""
        if self.url:
            return self._remove_http(code)
        return self._remove_file(code)
    
    def _publish_file(self, wc: WormholeCode) -> bool:
        """Publiceer naar lokaal bestand."""
        with self._lock:
            try:
                data = self._load_file()
                # Cleanup expired
                data = {k: v for k, v in data.items() 
                        if v.get("expires_at", 0) > time.time()}
                data[wc.code] = wc.to_dict()
                self._save_file(data)
                return True
            except Exception as e:
                print(f"[RENDEZVOUS] Publish error: {e}")
                return False
    
    def _lookup_file(self, code: str) -> Optional[WormholeCode]:
        """Zoek in lokaal bestand."""
        with self._lock:
            try:
                data = self._load_file()
                if code in data:
                    wc = WormholeCode.from_dict(data[code])
                    if not wc.is_expired():
                        return wc
            except Exception:
                pass
            return None
    
    def _remove_file(self, code: str) -> bool:
        """Verwijder uit lokaal bestand."""
        with self._lock:
            try:
                data = self._load_file()
                if code in data:
                    del data[code]
                    self._save_file(data)
                return True
            except Exception:
                return False
    
    def _load_file(self) -> dict:
        if self.file_path.exists():
            return json.loads(self.file_path.read_text())
        return {}
    
    def _save_file(self, data: dict):
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_path.write_text(json.dumps(data, indent=2))
    
    def _publish_http(self, wc: WormholeCode) -> bool:
        """Publiceer via HTTP POST."""
        try:
            req = Request(
                f"{self.url}/publish",
                data=json.dumps(wc.to_dict()).encode(),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except Exception as e:
            print(f"[RENDEZVOUS] HTTP publish error: {e}")
            return False
    
    def _lookup_http(self, code: str) -> Optional[WormholeCode]:
        """Zoek via HTTP GET."""
        try:
            with urlopen(f"{self.url}/lookup/{code}", timeout=10) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode())
                    return WormholeCode.from_dict(data)
        except Exception:
            pass
        return None
    
    def _remove_http(self, code: str) -> bool:
        """Verwijder via HTTP DELETE."""
        try:
            req = Request(f"{self.url}/remove/{code}", method="DELETE")
            with urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except Exception:
            return False

class RendezvousServer:
    """Simpele HTTP rendezvous server (self-hostable)."""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 9878):
        self.host = host
        self.port = port
        self.codes: Dict[str, dict] = {}
        self._lock = threading.Lock()
        self._server: Optional[HTTPServer] = None
    
    def start(self):
        """Start rendezvous server."""
        handler = self._create_handler()
        self._server = HTTPServer((self.host, self.port), handler)
        threading.Thread(target=self._server.serve_forever, daemon=True).start()
        print(f"[RENDEZVOUS] Server started on {self.host}:{self.port}")
    
    def stop(self):
        if self._server:
            self._server.shutdown()
    
    def _create_handler(self):
        server = self
        
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass  # Suppress logs
            
            def do_POST(self):
                if self.path == "/publish":
                    length = int(self.headers.get("Content-Length", 0))
                    data = json.loads(self.rfile.read(length).decode())
                    with server._lock:
                        server.codes[data["code"]] = data
                    self.send_response(200)
                    self.end_headers()
                else:
                    self.send_response(404)
                    self.end_headers()
            
            def do_GET(self):
                if self.path.startswith("/lookup/"):
                    code = self.path.split("/")[-1]
                    with server._lock:
                        if code in server.codes:
                            wc = server.codes[code]
                            if wc.get("expires_at", 0) > time.time():
                                self.send_response(200)
                                self.send_header("Content-Type", "application/json")
                                self.end_headers()
                                self.wfile.write(json.dumps(wc).encode())
                                return
                    self.send_response(404)
                    self.end_headers()
                else:
                    self.send_response(404)
                    self.end_headers()
            
            def do_DELETE(self):
                if self.path.startswith("/remove/"):
                    code = self.path.split("/")[-1]
                    with server._lock:
                        server.codes.pop(code, None)
                    self.send_response(200)
                    self.end_headers()
                else:
                    self.send_response(404)
                    self.end_headers()
        
        return Handler

# ============================================================================
# NODE IDENTITY
# ============================================================================

@dataclass
class NodeIdentity:
    """Persistent node identity."""
    node_id: str
    hostname: str
    platform: str
    created_at: str
    public_key: str = ""
    
    @classmethod
    def load_or_create(cls, path: Path) -> "NodeIdentity":
        if path.exists():
            try:
                d = json.loads(path.read_text())
                return cls(**d)
            except Exception:
                pass
        # Create new
        seed = secrets.token_bytes(32)
        identity = cls(
            node_id=os.environ.get("PAXECT_LINK_NODE_ID") or str(uuid.uuid4()),
            hostname=OSLayer.node_name,
            platform=OSLayer.system,
            created_at=datetime.now(timezone.utc).isoformat() + "Z",
            public_key=base64.b64encode(hashlib.sha256(seed).digest()).decode(),
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(identity.__dict__, indent=2))
        return identity
    
    def to_public(self) -> dict:
        return {"node_id": self.node_id, "hostname": self.hostname, 
                "platform": self.platform, "public_key": self.public_key}

# ============================================================================
# MESSAGE ENVELOPE (voor routing)
# ============================================================================

class MsgType(Enum):
    DATA = "DATA"
    HANDSHAKE = "HANDSHAKE"
    HANDSHAKE_ACK = "ACK"
    HEARTBEAT = "HB"
    ROUTE = "ROUTE"

@dataclass
class Envelope:
    """Message wrapper met routing metadata."""
    msg_id: str
    msg_type: MsgType
    source: str
    destination: str  # node_id of "*" voor broadcast
    ttl: int = MAX_TTL
    hops: List[str] = field(default_factory=list)
    timestamp: str = ""
    payload: bytes = b""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat() + "Z"
        if not self.msg_id:
            self.msg_id = str(uuid.uuid4())[:8]
    
    def add_hop(self, node_id: str):
        self.hops.append(node_id)
        self.ttl -= 1
    
    def can_forward(self) -> bool:
        return self.ttl > 0 and len(self.hops) < MAX_HOPS
    
    def visited(self, node_id: str) -> bool:
        return node_id in self.hops
    
    def to_bytes(self) -> bytes:
        hdr = json.dumps({
            "id": self.msg_id, "t": self.msg_type.value, "s": self.source,
            "d": self.destination, "ttl": self.ttl, "h": self.hops,
            "ts": self.timestamp, "pl": len(self.payload)
        }, separators=(",", ":")).encode()
        return struct.pack("!H", len(hdr)) + hdr + self.payload
    
    @classmethod
    def from_bytes(cls, data: bytes) -> "Envelope":
        hdr_len = struct.unpack("!H", data[:2])[0]
        hdr = json.loads(data[2:2+hdr_len])
        return cls(
            msg_id=hdr["id"], msg_type=MsgType(hdr["t"]), source=hdr["s"],
            destination=hdr["d"], ttl=hdr["ttl"], hops=hdr["h"],
            timestamp=hdr["ts"], payload=data[2+hdr_len:]
        )

# ============================================================================
# PEER & ROUTING
# ============================================================================

@dataclass
class PeerInfo:
    """Known peer."""
    node_id: str
    hostname: str = ""
    public_key: str = ""
    last_seen: float = 0.0
    socket_addr: Optional[Tuple[str, int]] = None
    fs_inbox: Optional[Path] = None
    failures: int = 0

@dataclass
class RouteEntry:
    """Route table entry."""
    destination: str
    next_hop: str
    metric: float
    expires: float
    
    def expired(self) -> bool:
        return time.time() > self.expires

class RoutingTable:
    """Simple routing table."""
    def __init__(self, local_id: str):
        self.local_id = local_id
        self.routes: Dict[str, RouteEntry] = {}
        self._lock = threading.Lock()
    
    def add(self, dest: str, next_hop: str, metric: float = 1.0):
        with self._lock:
            self.routes[dest] = RouteEntry(dest, next_hop, metric, 
                                           time.time() + ROUTE_EXPIRE_SEC)
    
    def get(self, dest: str) -> Optional[RouteEntry]:
        with self._lock:
            r = self.routes.get(dest)
            if r and not r.expired():
                return r
            return None
    
    def remove_via(self, node_id: str):
        with self._lock:
            self.routes = {d: r for d, r in self.routes.items() 
                          if r.next_hop != node_id}

# ============================================================================
# TRANSPORT ABSTRACTION
# ============================================================================

class Transport:
    """Abstract transport."""
    def send(self, env: Envelope, peer: PeerInfo) -> bool:
        raise NotImplementedError
    def start(self): pass
    def stop(self): pass

class FSTransport(Transport):
    """Filesystem transport via shared directory."""
    def __init__(self, shared: Path, node_id: str, on_msg: Callable):
        self.shared = shared
        self.node_id = node_id
        self.on_msg = on_msg
        self.inbox = shared / node_id / "inbox"
        self._running = False
        self._thread: Optional[threading.Thread] = None
    
    def start(self):
        self.inbox.mkdir(parents=True, exist_ok=True)
        # Presence file
        pf = self.shared / f"{self.node_id}.presence"
        pf.write_text(json.dumps({
            "node_id": self.node_id, "inbox": str(self.inbox),
            "ts": datetime.now(timezone.utc).isoformat() + "Z"
        }))
        self._running = True
        self._thread = threading.Thread(target=self._poll, daemon=True)
        self._thread.start()
    
    def stop(self):
        self._running = False
        (self.shared / f"{self.node_id}.presence").unlink(missing_ok=True)
    
    def send(self, env: Envelope, peer: PeerInfo) -> bool:
        if not peer.fs_inbox:
            return False
        try:
            dst = Path(peer.fs_inbox) / f"{env.msg_id}.msg"
            OSLayer.atomic_write(dst, env.to_bytes())
            return True
        except Exception:
            return False
    
    def _poll(self):
        while self._running:
            try:
                for f in self.inbox.glob("*.msg"):
                    try:
                        env = Envelope.from_bytes(f.read_bytes())
                        f.unlink()
                        self.on_msg(env, "FS")
                    except Exception:
                        f.unlink(missing_ok=True)
            except Exception:
                pass
            time.sleep(0.5)
    
    def discover_peers(self) -> List[dict]:
        peers = []
        try:
            for pf in self.shared.glob("*.presence"):
                if pf.stem != self.node_id:
                    try:
                        peers.append(json.loads(pf.read_text()))
                    except Exception:
                        pass
        except Exception:
            pass
        return peers

class SocketTransport(Transport):
    """TCP socket transport."""
    def __init__(self, host: str, port: int, node_id: str, on_msg: Callable):
        self.host, self.port, self.node_id = host, port, node_id
        self.on_msg = on_msg
        self.actual_port = port
        self._server: Optional[socket.socket] = None
        self._conns: Dict[str, socket.socket] = {}
        self._lock = threading.Lock()
        self._running = False
    
    def start(self):
        if self.port == 0:
            return  # Disabled
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind((self.host, self.port))
        self.actual_port = self._server.getsockname()[1]
        self._server.listen(5)
        self._server.settimeout(1.0)
        self._running = True
        threading.Thread(target=self._accept, daemon=True).start()
    
    def stop(self):
        self._running = False
        if self._server:
            self._server.close()
        with self._lock:
            for c in self._conns.values():
                c.close()
    
    def send(self, env: Envelope, peer: PeerInfo) -> bool:
        if not peer.socket_addr:
            return False
        try:
            conn = self._get_conn(peer)
            if not conn:
                return False
            data = env.to_bytes()
            conn.sendall(struct.pack("!I", len(data)) + data)
            return True
        except Exception:
            self._drop_conn(peer.node_id)
            return False
    
    def _get_conn(self, peer: PeerInfo) -> Optional[socket.socket]:
        with self._lock:
            if peer.node_id in self._conns:
                return self._conns[peer.node_id]
        try:
            c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            c.settimeout(5.0)
            c.connect(peer.socket_addr)
            with self._lock:
                self._conns[peer.node_id] = c
            threading.Thread(target=self._recv_loop, args=(c, peer.node_id), daemon=True).start()
            return c
        except Exception:
            return None
    
    def _drop_conn(self, node_id: str):
        with self._lock:
            c = self._conns.pop(node_id, None)
            if c:
                c.close()
    
    def _accept(self):
        while self._running:
            try:
                conn, _ = self._server.accept()
                threading.Thread(target=self._handle, args=(conn,), daemon=True).start()
            except socket.timeout:
                pass
            except Exception:
                break
    
    def _handle(self, conn: socket.socket):
        conn.settimeout(30.0)
        peer_id = None
        try:
            while self._running:
                env = self._recv_msg(conn)
                if not env:
                    break
                if not peer_id:
                    peer_id = env.source
                    with self._lock:
                        self._conns[peer_id] = conn
                self.on_msg(env, "SOCK")
        except Exception:
            pass
        finally:
            if peer_id:
                self._drop_conn(peer_id)
    
    def _recv_loop(self, conn: socket.socket, peer_id: str):
        try:
            while self._running:
                env = self._recv_msg(conn)
                if not env:
                    break
                self.on_msg(env, "SOCK")
        except Exception:
            pass
        finally:
            self._drop_conn(peer_id)
    
    def _recv_msg(self, conn: socket.socket) -> Optional[Envelope]:
        try:
            hdr = self._recv_n(conn, 4)
            if not hdr:
                return None
            ln = struct.unpack("!I", hdr)[0]
            data = self._recv_n(conn, ln)
            return Envelope.from_bytes(data) if data else None
        except Exception:
            return None
    
    def _recv_n(self, conn: socket.socket, n: int) -> Optional[bytes]:
        buf = b""
        while len(buf) < n:
            chunk = conn.recv(n - len(buf))
            if not chunk:
                return None
            buf += chunk
        return buf

# ============================================================================
# MULTI-BRIDGE
# ============================================================================

class Bridge:
    """Bridge connection point."""
    def __init__(self, name: str, transport: Transport):
        self.name = name
        self.transport = transport
        self.peers: Set[str] = set()

class MultiBridge:
    """Manages multiple bridges."""
    def __init__(self):
        self.bridges: Dict[str, Bridge] = {}
    
    def add(self, name: str, transport: Transport) -> Bridge:
        b = Bridge(name, transport)
        self.bridges[name] = b
        return b
    
    def get_bridge_for_peer(self, node_id: str) -> Optional[Bridge]:
        for b in self.bridges.values():
            if node_id in b.peers:
                return b
        return None
    
    def all_peers(self) -> Set[str]:
        return set().union(*(b.peers for b in self.bridges.values()))

# ============================================================================
# AUTONOMOUS ROUTER
# ============================================================================

class LinkRouter:
    """Central router - connects all components."""
    
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.identity = NodeIdentity.load_or_create(IDENTITY_FILE)
        self.routing = RoutingTable(self.identity.node_id)
        self.multi_bridge = MultiBridge()
        self.peers: Dict[str, PeerInfo] = {}
        self._peers_lock = threading.Lock()
        self._seen: Set[str] = set()
        self._seen_lock = threading.Lock()
        self._data_callback: Optional[Callable] = None
        
        # Transports
        self.fs_transport: Optional[FSTransport] = None
        self.sock_transport: Optional[SocketTransport] = None
    
    def start(self):
        print(f"=== PAXECT Link v{VERSION} — Multi-Bridge Router ===")
        print(f"Node ID : {self.identity.node_id}")
        print(f"Host    : {self.identity.hostname} ({self.identity.platform})")
        
        # FS Transport
        SHARED_DIR.mkdir(parents=True, exist_ok=True)
        self.fs_transport = FSTransport(SHARED_DIR, self.identity.node_id, self._on_message)
        self.fs_transport.start()
        self.multi_bridge.add("FS", self.fs_transport)
        print(f"FS Transport: {SHARED_DIR}")
        
        # Socket Transport
        if SOCKET_PORT > 0 or self.cfg.get("enable_socket"):
            port = SOCKET_PORT if SOCKET_PORT > 0 else 9876
            self.sock_transport = SocketTransport(SOCKET_HOST, port, 
                                                  self.identity.node_id, self._on_message)
            self.sock_transport.start()
            self.multi_bridge.add("SOCK", self.sock_transport)
            print(f"Socket Transport: {SOCKET_HOST}:{self.sock_transport.actual_port}")
        
        # Background threads
        threading.Thread(target=self._discovery_loop, daemon=True).start()
        threading.Thread(target=self._heartbeat_loop, daemon=True).start()
        
        # Initial handshake
        self._broadcast(MsgType.HANDSHAKE, self.identity.to_public())
        print("Router started\n")
    
    def stop(self):
        self._broadcast(MsgType.DATA, {"disconnect": True})
        if self.fs_transport:
            self.fs_transport.stop()
        if self.sock_transport:
            self.sock_transport.stop()
        print("Router stopped")
    
    def set_data_callback(self, cb: Callable):
        """Set callback for DATA messages."""
        self._data_callback = cb
    
    def send_to(self, dest_node: str, payload: bytes) -> bool:
        """Send data to specific node."""
        env = Envelope(
            msg_id=str(uuid.uuid4())[:8],
            msg_type=MsgType.DATA,
            source=self.identity.node_id,
            destination=dest_node,
            payload=payload
        )
        return self._route_message(env)
    
    def broadcast_data(self, payload: bytes):
        """Broadcast data to all peers."""
        self._broadcast(MsgType.DATA, payload if isinstance(payload, dict) else {"raw": base64.b64encode(payload).decode()})
    
    # ---- Internal ----
    
    def _on_message(self, env: Envelope, transport: str):
        """Handle incoming message."""
        # Dedup
        with self._seen_lock:
            if env.msg_id in self._seen:
                return
            self._seen.add(env.msg_id)
            if len(self._seen) > 10000:
                self._seen = set(list(self._seen)[-5000:])
        
        # Update peer
        self._touch_peer(env.source)
        
        # Route to us?
        if env.destination not in ("*", self.identity.node_id):
            if env.can_forward() and not env.visited(self.identity.node_id):
                env.add_hop(self.identity.node_id)
                self._route_message(env)
            return
        
        # Handle by type
        if env.msg_type == MsgType.HANDSHAKE:
            self._handle_handshake(env)
        elif env.msg_type == MsgType.HANDSHAKE_ACK:
            self._handle_ack(env)
        elif env.msg_type == MsgType.HEARTBEAT:
            self._send_to_peer(env.source, Envelope(
                msg_id="", msg_type=MsgType.HEARTBEAT, 
                source=self.identity.node_id, destination=env.source
            ))
        elif env.msg_type == MsgType.ROUTE:
            self._handle_route(env)
        elif env.msg_type == MsgType.DATA:
            if self._data_callback:
                self._data_callback(env)
    
    def _handle_handshake(self, env: Envelope):
        try:
            d = json.loads(env.payload) if env.payload else {}
        except Exception:
            d = {}
        peer = self._get_or_create_peer(env.source)
        peer.hostname = d.get("hostname", "")
        peer.public_key = d.get("public_key", "")
        peer.last_seen = time.time()
        # ACK
        self._send_to_peer(env.source, Envelope(
            msg_id="", msg_type=MsgType.HANDSHAKE_ACK,
            source=self.identity.node_id, destination=env.source,
            payload=json.dumps(self.identity.to_public()).encode()
        ))
        # Add direct route
        self.routing.add(env.source, env.source, 1.0)
        print(f"[PAIR] {peer.node_id} ({peer.hostname})")
    
    def _handle_ack(self, env: Envelope):
        try:
            d = json.loads(env.payload) if env.payload else {}
        except Exception:
            d = {}
        peer = self._get_or_create_peer(env.source)
        peer.hostname = d.get("hostname", "")
        peer.public_key = d.get("public_key", "")
        peer.last_seen = time.time()
        self.routing.add(env.source, env.source, 1.0)
        print(f"[ACK] {peer.node_id} ({peer.hostname})")
    
    def _handle_route(self, env: Envelope):
        try:
            d = json.loads(env.payload)
            for r in d.get("routes", []):
                dest = r["dest"]
                if dest != self.identity.node_id:
                    self.routing.add(dest, env.source, r.get("metric", 1) + 1)
        except Exception:
            pass
    
    def _route_message(self, env: Envelope) -> bool:
        """Route message to destination."""
        dest = env.destination
        
        # Direct peer?
        with self._peers_lock:
            peer = self.peers.get(dest)
        if peer:
            return self._send_to_peer(dest, env)
        
        # Check routing table
        route = self.routing.get(dest)
        if route:
            return self._send_to_peer(route.next_hop, env)
        
        # Broadcast als fallback
        if dest != "*":
            env.destination = "*"
        return self._broadcast_env(env)
    
    def _send_to_peer(self, node_id: str, env: Envelope) -> bool:
        with self._peers_lock:
            peer = self.peers.get(node_id)
        if not peer:
            return False
        
        # Try socket first, then FS
        if self.sock_transport and peer.socket_addr:
            if self.sock_transport.send(env, peer):
                return True
        if self.fs_transport and peer.fs_inbox:
            if self.fs_transport.send(env, peer):
                return True
        
        peer.failures += 1
        return False
    
    def _broadcast(self, msg_type: MsgType, data: dict):
        payload = json.dumps(data).encode() if isinstance(data, dict) else data
        env = Envelope(
            msg_id=str(uuid.uuid4())[:8],
            msg_type=msg_type,
            source=self.identity.node_id,
            destination="*",
            payload=payload
        )
        self._broadcast_env(env)
    
    def _broadcast_env(self, env: Envelope) -> bool:
        sent = False
        with self._peers_lock:
            peers = list(self.peers.values())
        for peer in peers:
            if peer.node_id not in env.hops:
                if self._send_to_peer(peer.node_id, env):
                    sent = True
        return sent
    
    def _touch_peer(self, node_id: str):
        with self._peers_lock:
            if node_id in self.peers:
                self.peers[node_id].last_seen = time.time()
    
    def _get_or_create_peer(self, node_id: str) -> PeerInfo:
        with self._peers_lock:
            if node_id not in self.peers:
                self.peers[node_id] = PeerInfo(node_id=node_id, last_seen=time.time())
            return self.peers[node_id]
    
    def _discovery_loop(self):
        """Discover peers via FS presence files."""
        while _running:
            try:
                if self.fs_transport:
                    for p in self.fs_transport.discover_peers():
                        nid = p.get("node_id")
                        if nid and nid != self.identity.node_id:
                            is_new = nid not in self.peers
                            peer = self._get_or_create_peer(nid)
                            peer.fs_inbox = Path(p.get("inbox", ""))
                            # Register in bridge
                            self.multi_bridge.bridges.get("FS", Bridge("FS", self.fs_transport)).peers.add(nid)
                            # Send handshake to new peer
                            if is_new:
                                print(f"[DISCOVERED] {nid}")
                                self._send_to_peer(nid, Envelope(
                                    msg_id="", msg_type=MsgType.HANDSHAKE,
                                    source=self.identity.node_id, destination=nid,
                                    payload=json.dumps(self.identity.to_public()).encode()
                                ))
            except Exception:
                pass
            time.sleep(5.0)
    
    def _heartbeat_loop(self):
        """Send heartbeats, cleanup dead peers."""
        while _running:
            try:
                now = time.time()
                with self._peers_lock:
                    peers = list(self.peers.items())
                
                for nid, peer in peers:
                    # Send heartbeat
                    self._send_to_peer(nid, Envelope(
                        msg_id="", msg_type=MsgType.HEARTBEAT,
                        source=self.identity.node_id, destination=nid
                    ))
                    # Check timeout
                    if now - peer.last_seen > HEARTBEAT_TIMEOUT:
                        print(f"[DEAD] {nid}")
                        self.routing.remove_via(nid)
                        with self._peers_lock:
                            self.peers.pop(nid, None)
                
                # Announce routes
                routes = [{"dest": self.identity.node_id, "metric": 0}]
                for dest, entry in list(self.routing.routes.items()):
                    if not entry.expired():
                        routes.append({"dest": dest, "metric": entry.metric})
                self._broadcast(MsgType.ROUTE, {"routes": routes})
                
            except Exception:
                pass
            time.sleep(HEARTBEAT_SEC)

# ============================================================================
# LEGACY V1.X COMPATIBILITY LAYER
# ============================================================================

def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

def log_event(cfg: dict, level: str, event: str, src=None, dst=None, 
              status: str = "ok", msg: str = None):
    """JSONL logging (v1.x compatible)."""
    levels = {"debug": 10, "info": 20, "warn": 30, "error": 40}
    if levels.get(level, 20) < levels.get(cfg.get("log_level", "info"), 20):
        return
    entry = {
        "datetime_utc": utc_now(), "level": level, "event": event,
        "src": str(src) if src else None, "dst": str(dst) if dst else None,
        "status": status, "message": msg, "version": VERSION
    }
    LOGFILE.parent.mkdir(parents=True, exist_ok=True)
    with LOGFILE.open("a") as f:
        f.write(json.dumps(entry) + "\n")

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def load_policy() -> dict:
    if CONFIG.exists():
        try:
            cfg = json.loads(CONFIG.read_text())
            for k, v in DEFAULT_POLICY.items():
                cfg.setdefault(k, v)
            return cfg
        except Exception:
            pass
    CONFIG.write_text(json.dumps(DEFAULT_POLICY, indent=2))
    return DEFAULT_POLICY.copy()

def policy_allows(cfg: dict, node: str, path: Path) -> Tuple[bool, str]:
    if node not in cfg.get("trusted_nodes", []):
        return False, f"untrusted:{node}"
    # Check suffixes (including double like .aead.freq)
    allowed = cfg.get("allowed_suffixes", [])
    suffix = "".join(path.suffixes)  # e.g. ".aead.freq"
    if suffix not in allowed and path.suffix not in allowed:
        return False, f"suffix:{suffix}"
    max_mb = cfg.get("max_file_mb", 256)
    if path.exists() and path.stat().st_size > max_mb * 1024 * 1024:
        return False, f"size:{path.stat().st_size}"
    return True, "ok"

def run_core(args: list) -> Tuple[bool, str]:
    try:
        r = subprocess.run(PAXECT_CORE + args, capture_output=True, check=True)
        return True, r.stdout.decode()
    except subprocess.CalledProcessError as e:
        return False, e.stderr.decode()

def run_aead(mode: str, src: Path, dst: Path) -> Tuple[bool, str]:
    """Run AEAD encrypt/decrypt. Returns (success, error_msg)."""
    if not PAXECT_AEAD:
        return True, "no_aead"  # AEAD not configured, skip
    
    args = PAXECT_AEAD + ["--mode", mode]
    if PAXECT_AEAD_PASS:
        args += ["--pass", PAXECT_AEAD_PASS]
    elif PAXECT_AEAD_PASS_FILE:
        args += ["--pass-file", PAXECT_AEAD_PASS_FILE]
    else:
        return False, "no passphrase configured (PAXECT_AEAD_PASS or PAXECT_AEAD_PASS_FILE)"
    
    try:
        with src.open("rb") as inf, dst.open("wb") as outf:
            r = subprocess.run(args, stdin=inf, stdout=outf, stderr=subprocess.PIPE, check=True)
        return True, ""
    except subprocess.CalledProcessError as e:
        dst.unlink(missing_ok=True)
        return False, e.stderr.decode()

def encode_file(cfg: dict, src: Path):
    """Encode: [AEAD encrypt] → Core encode → .freq"""
    # Skip .aead and .freq files
    if src.suffix in (".aead", ".freq"):
        return
    
    # Determine output paths
    if PAXECT_AEAD:
        aead_file = src.with_suffix(".aead")
        freq_file = src.with_suffix(".aead.freq")
    else:
        aead_file = None
        freq_file = src.with_suffix(".freq")
    
    if freq_file.exists():
        return
    
    # Step 1: AEAD encrypt (if configured)
    if PAXECT_AEAD:
        if aead_file.exists():
            pass  # already encrypted
        else:
            ok, err = run_aead("encrypt", src, aead_file)
            if not ok:
                log_event(cfg, "error", "aead_encrypt_error", src, status="error", msg=err)
                time.sleep(BACKOFF_SEC)
                return
            log_event(cfg, "info", "aead_encrypt", src, aead_file)
        encode_src = aead_file
    else:
        encode_src = src
    
    # Step 2: Core encode
    ok, out = run_core(["encode", "-i", str(encode_src), "-o", str(freq_file)])
    if ok:
        sha = sha256_file(freq_file)
        OSLayer.atomic_write(freq_file.with_suffix(".freq.sha256"), (sha + "\n").encode())
        log_event(cfg, "info", "encode", src, freq_file, msg=f"sha256={sha}")
        if cfg.get("auto_delete", True):
            src.unlink(missing_ok=True)
            if aead_file:
                aead_file.unlink(missing_ok=True)
    else:
        log_event(cfg, "error", "encode_error", src, status="error", msg=out)
        time.sleep(BACKOFF_SEC)

def decode_file(cfg: dict, src: Path):
    """Decode: Core decode → [AEAD decrypt] → outbox"""
    # Determine if this is an encrypted file
    is_encrypted = ".aead" in src.suffixes
    
    if is_encrypted:
        # .aead.freq → decode → .aead → decrypt → final
        aead_file = OUTBOX / src.name.replace(".freq", "")
        final_file = OUTBOX / src.name.replace(".aead.freq", "")
    else:
        # .freq → decode → final
        aead_file = None
        final_file = OUTBOX / src.with_suffix("").name
    
    if final_file.exists():
        return
    
    # Verify checksum
    side = src.with_suffix(src.suffix + ".sha256")
    if side.exists():
        want = side.read_text().strip()
        have = sha256_file(src)
        if not hmac.compare_digest(want, have):
            log_event(cfg, "error", "checksum_mismatch", src, status="error")
            return
    
    # Step 1: Core decode
    decode_dst = aead_file if is_encrypted else final_file
    ok, out = run_core(["decode", "-i", str(src), "-o", str(decode_dst)])
    if not ok:
        log_event(cfg, "error", "decode_error", src, status="error", msg=out)
        time.sleep(BACKOFF_SEC)
        return
    
    # Step 2: AEAD decrypt (if encrypted)
    if is_encrypted and PAXECT_AEAD:
        ok, err = run_aead("decrypt", aead_file, final_file)
        if not ok:
            log_event(cfg, "error", "aead_decrypt_error", aead_file, status="error", msg=err)
            aead_file.unlink(missing_ok=True)
            return
        log_event(cfg, "info", "aead_decrypt", aead_file, final_file)
        aead_file.unlink(missing_ok=True)
    
    log_event(cfg, "info", "decode", src, final_file)
    if cfg.get("auto_delete", True):
        src.unlink(missing_ok=True)
        side.unlink(missing_ok=True)

# ============================================================================
# MAIN WITH CLI
# ============================================================================

def _sigterm(_s, _f):
    global _running
    _running = False

def share_mode(identity: "NodeIdentity", cfg: dict) -> str:
    """Start in share mode: genereer code en wacht op connectie."""
    rendezvous = RendezvousClient(RENDEZVOUS_URL, RENDEZVOUS_FILE)
    
    # Bepaal socket adres als socket enabled
    socket_addr = None
    if SOCKET_PORT > 0:
        ip = OSLayer.get_local_ip()
        socket_addr = (ip, SOCKET_PORT)
    
    # Genereer code
    code = generate_wormhole_code()
    wc = WormholeCode(
        code=code,
        node_id=identity.node_id,
        hostname=identity.hostname,
        public_key=identity.public_key,
        socket_addr=socket_addr,
    )
    
    # Publiceer
    if rendezvous.publish(wc):
        print(f"\n{'='*50}")
        print(f"  PAIRING CODE: {code}")
        print(f"{'='*50}")
        print(f"\n  Deel deze code met de andere node.")
        print(f"  De andere node voert uit:")
        print(f"    python3 paxect_link_plugin_v2.py --connect {code}")
        print(f"\n  Code verloopt over {CODE_EXPIRY_SEC // 60} minuten.")
        print(f"  Wachten op connectie...\n")
        return code
    else:
        print("[ERROR] Kon code niet publiceren")
        return ""

def connect_mode(code: str, identity: "NodeIdentity", cfg: dict) -> Optional[WormholeCode]:
    """Connect met een gedeelde code."""
    rendezvous = RendezvousClient(RENDEZVOUS_URL, RENDEZVOUS_FILE)
    
    print(f"\n[CONNECT] Zoeken naar code: {code}")
    
    # Zoek de code
    wc = rendezvous.lookup(code)
    if not wc:
        print(f"[ERROR] Code '{code}' niet gevonden of verlopen")
        return None
    
    if wc.is_expired():
        print(f"[ERROR] Code '{code}' is verlopen")
        return None
    
    print(f"[FOUND] Node gevonden:")
    print(f"  - Node ID  : {wc.node_id}")
    print(f"  - Hostname : {wc.hostname}")
    if wc.socket_addr:
        print(f"  - Socket   : {wc.socket_addr[0]}:{wc.socket_addr[1]}")
    
    # Voeg toe aan trusted_nodes en policy
    if wc.node_id not in cfg.get("trusted_nodes", []):
        cfg["trusted_nodes"].append(wc.node_id)
    if wc.hostname not in cfg.get("trusted_nodes", []):
        cfg["trusted_nodes"].append(wc.hostname)
    
    # Sla bijgewerkte policy op
    CONFIG.write_text(json.dumps(cfg, indent=2))
    print(f"[POLICY] {wc.node_id} toegevoegd aan trusted_nodes")
    
    # Publiceer onze eigen info als response
    our_wc = WormholeCode(
        code=code + "-accept",
        node_id=identity.node_id,
        hostname=identity.hostname,
        public_key=identity.public_key,
        socket_addr=(OSLayer.get_local_ip(), SOCKET_PORT) if SOCKET_PORT > 0 else None,
    )
    rendezvous.publish(our_wc)
    
    # Cleanup originele code
    rendezvous.remove(code)
    
    print(f"\n[SUCCESS] Verbonden met {wc.hostname}!")
    return wc

def wait_for_accept(code: str, identity: "NodeIdentity", cfg: dict, timeout: int = 300) -> Optional[WormholeCode]:
    """Wacht tot iemand onze code accepteert."""
    rendezvous = RendezvousClient(RENDEZVOUS_URL, RENDEZVOUS_FILE)
    accept_code = code + "-accept"
    start = time.time()
    
    while time.time() - start < timeout:
        wc = rendezvous.lookup(accept_code)
        if wc:
            print(f"\n[ACCEPTED] Verbonden met {wc.hostname}!")
            
            # Voeg toe aan policy
            if wc.node_id not in cfg.get("trusted_nodes", []):
                cfg["trusted_nodes"].append(wc.node_id)
            if wc.hostname not in cfg.get("trusted_nodes", []):
                cfg["trusted_nodes"].append(wc.hostname)
            CONFIG.write_text(json.dumps(cfg, indent=2))
            
            # Cleanup
            rendezvous.remove(code)
            rendezvous.remove(accept_code)
            
            return wc
        
        time.sleep(2)
    
    print("\n[TIMEOUT] Geen connectie ontvangen")
    rendezvous.remove(code)
    return None

def run_normal_mode(cfg: dict):
    """Run in normale watch mode."""
    global _running
    
    print(f"=== PAXECT Link Plugin v{VERSION} ===")
    print(f"Script  : {Path(__file__).resolve()}")
    print(f"Time    : {utc_now()}")
    print(f"Inbox   : {INBOX.resolve()}")
    print(f"Outbox  : {OUTBOX.resolve()}")
    print(f"Shared  : {SHARED_DIR.resolve()}")
    print()
    
    INBOX.mkdir(parents=True, exist_ok=True)
    OUTBOX.mkdir(parents=True, exist_ok=True)
    
    # Single instance lock
    try:
        fd = os.open(LOCKFILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "w") as f:
            f.write(f"{os.getpid()}\n")
    except FileExistsError:
        print("[LINK] Another instance running. Exit.")
        return
    
    signal.signal(signal.SIGINT, _sigterm)
    signal.signal(signal.SIGTERM, _sigterm)
    
    try:
        # Start router (v2.0)
        router = LinkRouter(cfg)
        router.start()
        
        # Data callback: relay ontvangen data naar outbox
        def on_data(env: Envelope):
            if env.payload:
                ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                out = OUTBOX / f"relay_{env.source}_{ts}.bin"
                out.write_bytes(env.payload)
                log_event(cfg, "info", "relay_recv", env.source, out)
        
        router.set_data_callback(on_data)
        
        log_event(cfg, "info", "startup", INBOX, OUTBOX, msg=f"v{VERSION}")
        print("[LINK] Watching... (Ctrl+C to stop)\n")
        
        node = OSLayer.node_name
        
        while _running:
            # V1.x compatible: local inbox processing
            for f in INBOX.iterdir():
                if not f.is_file() or f.name.startswith(".") or f.suffix in (".part", ".tmp"):
                    continue
                ok, reason = policy_allows(cfg, node, f)
                if not ok:
                    log_event(cfg, "warn", "policy_block", f, status="warn", msg=reason)
                    continue
                if f.suffix == ".freq":
                    decode_file(cfg, f)
                else:
                    encode_file(cfg, f)
            
            time.sleep(POLL_INTERVAL)
        
        print("\n[LINK] Stopping...")
        router.stop()
        
    finally:
        log_event(cfg, "info", "shutdown", status="ok")
        LOCKFILE.unlink(missing_ok=True)

def main():
    global _running
    
    parser = argparse.ArgumentParser(
        description="PAXECT Link Plugin v2.1 - Multi-Bridge Relay with Wormhole Discovery",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Voorbeelden:
  # Normaal draaien (watch mode):
  python3 paxect_link_plugin_v2.py

  # Deel een pairing code:
  python3 paxect_link_plugin_v2.py --share

  # Verbind met een code:
  python3 paxect_link_plugin_v2.py --connect 7-tiger-mountain

  # Start rendezvous server:
  python3 paxect_link_plugin_v2.py --rendezvous-server --port 9878
"""
    )
    
    parser.add_argument("--share", action="store_true",
                        help="Genereer pairing code en wacht op connectie")
    parser.add_argument("--connect", metavar="CODE",
                        help="Verbind met een pairing code")
    parser.add_argument("--rendezvous-server", action="store_true",
                        help="Start als rendezvous server")
    parser.add_argument("--port", type=int, default=9878,
                        help="Port voor rendezvous server (default: 9878)")
    parser.add_argument("--list-peers", action="store_true",
                        help="Toon bekende peers")
    parser.add_argument("--version", action="version", version=f"PAXECT Link v{VERSION}")
    
    args = parser.parse_args()
    
    # Load config and identity
    cfg = load_policy()
    identity = NodeIdentity.load_or_create(IDENTITY_FILE)
    
    if args.rendezvous_server:
        # Run as rendezvous server
        print(f"=== PAXECT Rendezvous Server ===")
        server = RendezvousServer("0.0.0.0", args.port)
        server.start()
        print(f"Server draait op port {args.port}")
        print("Ctrl+C om te stoppen...")
        
        signal.signal(signal.SIGINT, _sigterm)
        signal.signal(signal.SIGTERM, _sigterm)
        
        while _running:
            time.sleep(1)
        
        server.stop()
        return
    
    if args.share:
        # Share mode
        INBOX.mkdir(parents=True, exist_ok=True)
        OUTBOX.mkdir(parents=True, exist_ok=True)
        
        code = share_mode(identity, cfg)
        if code:
            # Wacht op accept, dan start normal mode
            peer = wait_for_accept(code, identity, cfg)
            if peer:
                print(f"\n[START] Starten in normal mode...\n")
                run_normal_mode(cfg)
        return
    
    if args.connect:
        # Connect mode
        INBOX.mkdir(parents=True, exist_ok=True)
        OUTBOX.mkdir(parents=True, exist_ok=True)
        
        peer = connect_mode(args.connect, identity, cfg)
        if peer:
            print(f"\n[START] Starten in normal mode...\n")
            run_normal_mode(cfg)
        return
    
    if args.list_peers:
        # List known peers
        print(f"=== Bekende Peers ===")
        print(f"Trusted nodes: {cfg.get('trusted_nodes', [])}")
        return
    
    # Default: normal mode
    run_normal_mode(cfg)

if __name__ == "__main__":
    main()
    "log_level": "info",
    # v2.0 additions
    "enable_socket": False,
    "enable_routing": True,
    "enable_aead": False,  # set True to require AEAD
}

_running = True

# ============================================================================
# OS ABSTRACTION LAYER
# ============================================================================

class OSLayer:
    """Cross-platform abstraction."""
    system = platform.system()
    node_name = platform.node() or "localhost"
    is_windows = system == "Windows"
    
    @staticmethod
    def atomic_write(path: Path, data: bytes):
        tmp = path.with_suffix(path.suffix + ".tmp")
        try:
            with tmp.open("wb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            tmp.replace(path)
        except Exception:
            tmp.unlink(missing_ok=True)
            raise
    
    @staticmethod
    def get_local_ip() -> str:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

# ============================================================================
# WORMHOLE-STYLE DISCOVERY
# ============================================================================

def generate_wormhole_code() -> str:
    """Genereer menselijke code: nummer-bijvoeglijk-zelfstandig."""
    num = random.randint(1, 999)
    adj = random.choice(WORDLIST_ADJ)
    noun = random.choice(WORDLIST_NOUN)
    return f"{num}-{adj}-{noun}"

def generate_short_code(length: int = 6) -> str:
    """Genereer korte alfanumerieke code."""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

@dataclass
class WormholeCode:
    """Wormhole code met connection info."""
    code: str
    node_id: str
    hostname: str
    public_key: str
    socket_addr: Optional[Tuple[str, int]] = None  # (ip, port)
    created_at: float = 0.0
    expires_at: float = 0.0
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = time.time()
        if not self.expires_at:
            self.expires_at = self.created_at + CODE_EXPIRY_SEC
    
    def is_expired(self) -> bool:
        return time.time() > self.expires_at
    
    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "node_id": self.node_id,
            "hostname": self.hostname,
            "public_key": self.public_key,
            "socket_addr": list(self.socket_addr) if self.socket_addr else None,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
        }
    
    @classmethod
    def from_dict(cls, d: dict) -> "WormholeCode":
        return cls(
            code=d["code"],
            node_id=d["node_id"],
            hostname=d["hostname"],
            public_key=d.get("public_key", ""),
            socket_addr=tuple(d["socket_addr"]) if d.get("socket_addr") else None,
            created_at=d.get("created_at", 0),
            expires_at=d.get("expires_at", 0),
        )

class RendezvousClient:
    """Client voor rendezvous server (file-based of HTTP)."""
    
    def __init__(self, url: str = "", file_path: Path = RENDEZVOUS_FILE):
        self.url = url
        self.file_path = file_path
        self._lock = threading.Lock()
    
    def publish(self, wc: WormholeCode) -> bool:
        """Publiceer code naar rendezvous."""
        if self.url:
            return self._publish_http(wc)
        return self._publish_file(wc)
    
    def lookup(self, code: str) -> Optional[WormholeCode]:
        """Zoek code op bij rendezvous."""
        if self.url:
            return self._lookup_http(code)
        return self._lookup_file(code)
    
    def remove(self, code: str) -> bool:
        """Verwijder code van rendezvous."""
        if self.url:
            return self._remove_http(code)
        return self._remove_file(code)
    
    def _publish_file(self, wc: WormholeCode) -> bool:
        """Publiceer naar lokaal bestand."""
        with self._lock:
            try:
                data = self._load_file()
                # Cleanup expired
                data = {k: v for k, v in data.items() 
                        if v.get("expires_at", 0) > time.time()}
                data[wc.code] = wc.to_dict()
                self._save_file(data)
                return True
            except Exception as e:
                print(f"[RENDEZVOUS] Publish error: {e}")
                return False
    
    def _lookup_file(self, code: str) -> Optional[WormholeCode]:
        """Zoek in lokaal bestand."""
        with self._lock:
            try:
                data = self._load_file()
                if code in data:
                    wc = WormholeCode.from_dict(data[code])
                    if not wc.is_expired():
                        return wc
            except Exception:
                pass
            return None
    
    def _remove_file(self, code: str) -> bool:
        """Verwijder uit lokaal bestand."""
        with self._lock:
            try:
                data = self._load_file()
                if code in data:
                    del data[code]
                    self._save_file(data)
                return True
            except Exception:
                return False
    
    def _load_file(self) -> dict:
        if self.file_path.exists():
            return json.loads(self.file_path.read_text())
        return {}
    
    def _save_file(self, data: dict):
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_path.write_text(json.dumps(data, indent=2))
    
    def _publish_http(self, wc: WormholeCode) -> bool:
        """Publiceer via HTTP POST."""
        try:
            req = Request(
                f"{self.url}/publish",
                data=json.dumps(wc.to_dict()).encode(),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except Exception as e:
            print(f"[RENDEZVOUS] HTTP publish error: {e}")
            return False
    
    def _lookup_http(self, code: str) -> Optional[WormholeCode]:
        """Zoek via HTTP GET."""
        try:
            with urlopen(f"{self.url}/lookup/{code}", timeout=10) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode())
                    return WormholeCode.from_dict(data)
        except Exception:
            pass
        return None
    
    def _remove_http(self, code: str) -> bool:
        """Verwijder via HTTP DELETE."""
        try:
            req = Request(f"{self.url}/remove/{code}", method="DELETE")
            with urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except Exception:
            return False

class RendezvousServer:
    """Simpele HTTP rendezvous server (self-hostable)."""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 9878):
        self.host = host
        self.port = port
        self.codes: Dict[str, dict] = {}
        self._lock = threading.Lock()
        self._server: Optional[HTTPServer] = None
    
    def start(self):
        """Start rendezvous server."""
        handler = self._create_handler()
        self._server = HTTPServer((self.host, self.port), handler)
        threading.Thread(target=self._server.serve_forever, daemon=True).start()
        print(f"[RENDEZVOUS] Server started on {self.host}:{self.port}")
    
    def stop(self):
        if self._server:
            self._server.shutdown()
    
    def _create_handler(self):
        server = self
        
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass  # Suppress logs
            
            def do_POST(self):
                if self.path == "/publish":
                    length = int(self.headers.get("Content-Length", 0))
                    data = json.loads(self.rfile.read(length).decode())
                    with server._lock:
                        server.codes[data["code"]] = data
                    self.send_response(200)
                    self.end_headers()
                else:
                    self.send_response(404)
                    self.end_headers()
            
            def do_GET(self):
                if self.path.startswith("/lookup/"):
                    code = self.path.split("/")[-1]
                    with server._lock:
                        if code in server.codes:
                            wc = server.codes[code]
                            if wc.get("expires_at", 0) > time.time():
                                self.send_response(200)
                                self.send_header("Content-Type", "application/json")
                                self.end_headers()
                                self.wfile.write(json.dumps(wc).encode())
                                return
                    self.send_response(404)
                    self.end_headers()
                else:
                    self.send_response(404)
                    self.end_headers()
            
            def do_DELETE(self):
                if self.path.startswith("/remove/"):
                    code = self.path.split("/")[-1]
                    with server._lock:
                        server.codes.pop(code, None)
                    self.send_response(200)
                    self.end_headers()
                else:
                    self.send_response(404)
                    self.end_headers()
        
        return Handler

# ============================================================================
# NODE IDENTITY
# ============================================================================

@dataclass
class NodeIdentity:
    """Persistent node identity."""
    node_id: str
    hostname: str
    platform: str
    created_at: str
    public_key: str = ""
    
    @classmethod
    def load_or_create(cls, path: Path) -> "NodeIdentity":
        if path.exists():
            try:
                d = json.loads(path.read_text())
                return cls(**d)
            except Exception:
                pass
        # Create new
        seed = secrets.token_bytes(32)
        identity = cls(
            node_id=os.environ.get("PAXECT_LINK_NODE_ID") or str(uuid.uuid4()),
            hostname=OSLayer.node_name,
            platform=OSLayer.system,
            created_at=datetime.now(timezone.utc).isoformat() + "Z",
            public_key=base64.b64encode(hashlib.sha256(seed).digest()).decode(),
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(identity.__dict__, indent=2))
        return identity
    
    def to_public(self) -> dict:
        return {"node_id": self.node_id, "hostname": self.hostname, 
                "platform": self.platform, "public_key": self.public_key}

# ============================================================================
# MESSAGE ENVELOPE (voor routing)
# ============================================================================

class MsgType(Enum):
    DATA = "DATA"
    HANDSHAKE = "HANDSHAKE"
    HANDSHAKE_ACK = "ACK"
    HEARTBEAT = "HB"
    ROUTE = "ROUTE"

@dataclass
class Envelope:
    """Message wrapper met routing metadata."""
    msg_id: str
    msg_type: MsgType
    source: str
    destination: str  # node_id of "*" voor broadcast
    ttl: int = MAX_TTL
    hops: List[str] = field(default_factory=list)
    timestamp: str = ""
    payload: bytes = b""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat() + "Z"
        if not self.msg_id:
            self.msg_id = str(uuid.uuid4())[:8]
    
    def add_hop(self, node_id: str):
        self.hops.append(node_id)
        self.ttl -= 1
    
    def can_forward(self) -> bool:
        return self.ttl > 0 and len(self.hops) < MAX_HOPS
    
    def visited(self, node_id: str) -> bool:
        return node_id in self.hops
    
    def to_bytes(self) -> bytes:
        hdr = json.dumps({
            "id": self.msg_id, "t": self.msg_type.value, "s": self.source,
            "d": self.destination, "ttl": self.ttl, "h": self.hops,
            "ts": self.timestamp, "pl": len(self.payload)
        }, separators=(",", ":")).encode()
        return struct.pack("!H", len(hdr)) + hdr + self.payload
    
    @classmethod
    def from_bytes(cls, data: bytes) -> "Envelope":
        hdr_len = struct.unpack("!H", data[:2])[0]
        hdr = json.loads(data[2:2+hdr_len])
        return cls(
            msg_id=hdr["id"], msg_type=MsgType(hdr["t"]), source=hdr["s"],
            destination=hdr["d"], ttl=hdr["ttl"], hops=hdr["h"],
            timestamp=hdr["ts"], payload=data[2+hdr_len:]
        )

# ============================================================================
# PEER & ROUTING
# ============================================================================

@dataclass
class PeerInfo:
    """Known peer."""
    node_id: str
    hostname: str = ""
    public_key: str = ""
    last_seen: float = 0.0
    socket_addr: Optional[Tuple[str, int]] = None
    fs_inbox: Optional[Path] = None
    failures: int = 0

@dataclass
class RouteEntry:
    """Route table entry."""
    destination: str
    next_hop: str
    metric: float
    expires: float
    
    def expired(self) -> bool:
        return time.time() > self.expires

class RoutingTable:
    """Simple routing table."""
    def __init__(self, local_id: str):
        self.local_id = local_id
        self.routes: Dict[str, RouteEntry] = {}
        self._lock = threading.Lock()
    
    def add(self, dest: str, next_hop: str, metric: float = 1.0):
        with self._lock:
            self.routes[dest] = RouteEntry(dest, next_hop, metric, 
                                           time.time() + ROUTE_EXPIRE_SEC)
    
    def get(self, dest: str) -> Optional[RouteEntry]:
        with self._lock:
            r = self.routes.get(dest)
            if r and not r.expired():
                return r
            return None
    
    def remove_via(self, node_id: str):
        with self._lock:
            self.routes = {d: r for d, r in self.routes.items() 
                          if r.next_hop != node_id}

# ============================================================================
# TRANSPORT ABSTRACTION
# ============================================================================

class Transport:
    """Abstract transport."""
    def send(self, env: Envelope, peer: PeerInfo) -> bool:
        raise NotImplementedError
    def start(self): pass
    def stop(self): pass

class FSTransport(Transport):
    """Filesystem transport via shared directory."""
    def __init__(self, shared: Path, node_id: str, on_msg: Callable):
        self.shared = shared
        self.node_id = node_id
        self.on_msg = on_msg
        self.inbox = shared / node_id / "inbox"
        self._running = False
        self._thread: Optional[threading.Thread] = None
    
    def start(self):
        self.inbox.mkdir(parents=True, exist_ok=True)
        # Presence file
        pf = self.shared / f"{self.node_id}.presence"
        pf.write_text(json.dumps({
            "node_id": self.node_id, "inbox": str(self.inbox),
            "ts": datetime.now(timezone.utc).isoformat() + "Z"
        }))
        self._running = True
        self._thread = threading.Thread(target=self._poll, daemon=True)
        self._thread.start()
    
    def stop(self):
        self._running = False
        (self.shared / f"{self.node_id}.presence").unlink(missing_ok=True)
    
    def send(self, env: Envelope, peer: PeerInfo) -> bool:
        if not peer.fs_inbox:
            return False
        try:
            dst = Path(peer.fs_inbox) / f"{env.msg_id}.msg"
            OSLayer.atomic_write(dst, env.to_bytes())
            return True
        except Exception:
            return False
    
    def _poll(self):
        while self._running:
            try:
                for f in self.inbox.glob("*.msg"):
                    try:
                        env = Envelope.from_bytes(f.read_bytes())
                        f.unlink()
                        self.on_msg(env, "FS")
                    except Exception:
                        f.unlink(missing_ok=True)
            except Exception:
                pass
            time.sleep(0.5)
    
    def discover_peers(self) -> List[dict]:
        peers = []
        try:
            for pf in self.shared.glob("*.presence"):
                if pf.stem != self.node_id:
                    try:
                        peers.append(json.loads(pf.read_text()))
                    except Exception:
                        pass
        except Exception:
            pass
        return peers

class SocketTransport(Transport):
    """TCP socket transport."""
    def __init__(self, host: str, port: int, node_id: str, on_msg: Callable):
        self.host, self.port, self.node_id = host, port, node_id
        self.on_msg = on_msg
        self.actual_port = port
        self._server: Optional[socket.socket] = None
        self._conns: Dict[str, socket.socket] = {}
        self._lock = threading.Lock()
        self._running = False
    
    def start(self):
        if self.port == 0:
            return  # Disabled
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind((self.host, self.port))
        self.actual_port = self._server.getsockname()[1]
        self._server.listen(5)
        self._server.settimeout(1.0)
        self._running = True
        threading.Thread(target=self._accept, daemon=True).start()
    
    def stop(self):
        self._running = False
        if self._server:
            self._server.close()
        with self._lock:
            for c in self._conns.values():
                c.close()
    
    def send(self, env: Envelope, peer: PeerInfo) -> bool:
        if not peer.socket_addr:
            return False
        try:
            conn = self._get_conn(peer)
            if not conn:
                return False
            data = env.to_bytes()
            conn.sendall(struct.pack("!I", len(data)) + data)
            return True
        except Exception:
            self._drop_conn(peer.node_id)
            return False
    
    def _get_conn(self, peer: PeerInfo) -> Optional[socket.socket]:
        with self._lock:
            if peer.node_id in self._conns:
                return self._conns[peer.node_id]
        try:
            c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            c.settimeout(5.0)
            c.connect(peer.socket_addr)
            with self._lock:
                self._conns[peer.node_id] = c
            threading.Thread(target=self._recv_loop, args=(c, peer.node_id), daemon=True).start()
            return c
        except Exception:
            return None
    
    def _drop_conn(self, node_id: str):
        with self._lock:
            c = self._conns.pop(node_id, None)
            if c:
                c.close()
    
    def _accept(self):
        while self._running:
            try:
                conn, _ = self._server.accept()
                threading.Thread(target=self._handle, args=(conn,), daemon=True).start()
            except socket.timeout:
                pass
            except Exception:
                break
    
    def _handle(self, conn: socket.socket):
        conn.settimeout(30.0)
        peer_id = None
        try:
            while self._running:
                env = self._recv_msg(conn)
                if not env:
                    break
                if not peer_id:
                    peer_id = env.source
                    with self._lock:
                        self._conns[peer_id] = conn
                self.on_msg(env, "SOCK")
        except Exception:
            pass
        finally:
            if peer_id:
                self._drop_conn(peer_id)
    
    def _recv_loop(self, conn: socket.socket, peer_id: str):
        try:
            while self._running:
                env = self._recv_msg(conn)
                if not env:
                    break
                self.on_msg(env, "SOCK")
        except Exception:
            pass
        finally:
            self._drop_conn(peer_id)
    
    def _recv_msg(self, conn: socket.socket) -> Optional[Envelope]:
        try:
            hdr = self._recv_n(conn, 4)
            if not hdr:
                return None
            ln = struct.unpack("!I", hdr)[0]
            data = self._recv_n(conn, ln)
            return Envelope.from_bytes(data) if data else None
        except Exception:
            return None
    
    def _recv_n(self, conn: socket.socket, n: int) -> Optional[bytes]:
        buf = b""
        while len(buf) < n:
            chunk = conn.recv(n - len(buf))
            if not chunk:
                return None
            buf += chunk
        return buf

# ============================================================================
# MULTI-BRIDGE
# ============================================================================

class Bridge:
    """Bridge connection point."""
    def __init__(self, name: str, transport: Transport):
        self.name = name
        self.transport = transport
        self.peers: Set[str] = set()

class MultiBridge:
    """Manages multiple bridges."""
    def __init__(self):
        self.bridges: Dict[str, Bridge] = {}
    
    def add(self, name: str, transport: Transport) -> Bridge:
        b = Bridge(name, transport)
        self.bridges[name] = b
        return b
    
    def get_bridge_for_peer(self, node_id: str) -> Optional[Bridge]:
        for b in self.bridges.values():
            if node_id in b.peers:
                return b
        return None
    
    def all_peers(self) -> Set[str]:
        return set().union(*(b.peers for b in self.bridges.values()))

# ============================================================================
# AUTONOMOUS ROUTER
# ============================================================================

class LinkRouter:
    """Central router - connects all components."""
    
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.identity = NodeIdentity.load_or_create(IDENTITY_FILE)
        self.routing = RoutingTable(self.identity.node_id)
        self.multi_bridge = MultiBridge()
        self.peers: Dict[str, PeerInfo] = {}
        self._peers_lock = threading.Lock()
        self._seen: Set[str] = set()
        self._seen_lock = threading.Lock()
        self._data_callback: Optional[Callable] = None
        
        # Transports
        self.fs_transport: Optional[FSTransport] = None
        self.sock_transport: Optional[SocketTransport] = None
    
    def start(self):
        print(f"=== PAXECT Link v{VERSION} — Multi-Bridge Router ===")
        print(f"Node ID : {self.identity.node_id}")
        print(f"Host    : {self.identity.hostname} ({self.identity.platform})")
        
        # FS Transport
        SHARED_DIR.mkdir(parents=True, exist_ok=True)
        self.fs_transport = FSTransport(SHARED_DIR, self.identity.node_id, self._on_message)
        self.fs_transport.start()
        self.multi_bridge.add("FS", self.fs_transport)
        print(f"FS Transport: {SHARED_DIR}")
        
        # Socket Transport
        if SOCKET_PORT > 0 or self.cfg.get("enable_socket"):
            port = SOCKET_PORT if SOCKET_PORT > 0 else 9876
            self.sock_transport = SocketTransport(SOCKET_HOST, port, 
                                                  self.identity.node_id, self._on_message)
            self.sock_transport.start()
            self.multi_bridge.add("SOCK", self.sock_transport)
            print(f"Socket Transport: {SOCKET_HOST}:{self.sock_transport.actual_port}")
        
        # Background threads
        threading.Thread(target=self._discovery_loop, daemon=True).start()
        threading.Thread(target=self._heartbeat_loop, daemon=True).start()
        
        # Initial handshake
        self._broadcast(MsgType.HANDSHAKE, self.identity.to_public())
        print("Router started\n")
    
    def stop(self):
        self._broadcast(MsgType.DATA, {"disconnect": True})
        if self.fs_transport:
            self.fs_transport.stop()
        if self.sock_transport:
            self.sock_transport.stop()
        print("Router stopped")
    
    def set_data_callback(self, cb: Callable):
        """Set callback for DATA messages."""
        self._data_callback = cb
    
    def send_to(self, dest_node: str, payload: bytes) -> bool:
        """Send data to specific node."""
        env = Envelope(
            msg_id=str(uuid.uuid4())[:8],
            msg_type=MsgType.DATA,
            source=self.identity.node_id,
            destination=dest_node,
            payload=payload
        )
        return self._route_message(env)
    
    def broadcast_data(self, payload: bytes):
        """Broadcast data to all peers."""
        self._broadcast(MsgType.DATA, payload if isinstance(payload, dict) else {"raw": base64.b64encode(payload).decode()})
    
    # ---- Internal ----
    
    def _on_message(self, env: Envelope, transport: str):
        """Handle incoming message."""
        # Dedup
        with self._seen_lock:
            if env.msg_id in self._seen:
                return
            self._seen.add(env.msg_id)
            if len(self._seen) > 10000:
                self._seen = set(list(self._seen)[-5000:])
        
        # Update peer
        self._touch_peer(env.source)
        
        # Route to us?
        if env.destination not in ("*", self.identity.node_id):
            if env.can_forward() and not env.visited(self.identity.node_id):
                env.add_hop(self.identity.node_id)
                self._route_message(env)
            return
        
        # Handle by type
        if env.msg_type == MsgType.HANDSHAKE:
            self._handle_handshake(env)
        elif env.msg_type == MsgType.HANDSHAKE_ACK:
            self._handle_ack(env)
        elif env.msg_type == MsgType.HEARTBEAT:
            self._send_to_peer(env.source, Envelope(
                msg_id="", msg_type=MsgType.HEARTBEAT, 
                source=self.identity.node_id, destination=env.source
            ))
        elif env.msg_type == MsgType.ROUTE:
            self._handle_route(env)
        elif env.msg_type == MsgType.DATA:
            if self._data_callback:
                self._data_callback(env)
    
    def _handle_handshake(self, env: Envelope):
        try:
            d = json.loads(env.payload) if env.payload else {}
        except Exception:
            d = {}
        peer = self._get_or_create_peer(env.source)
        peer.hostname = d.get("hostname", "")
        peer.public_key = d.get("public_key", "")
        peer.last_seen = time.time()
        # ACK
        self._send_to_peer(env.source, Envelope(
            msg_id="", msg_type=MsgType.HANDSHAKE_ACK,
            source=self.identity.node_id, destination=env.source,
            payload=json.dumps(self.identity.to_public()).encode()
        ))
        # Add direct route
        self.routing.add(env.source, env.source, 1.0)
        print(f"[PAIR] {peer.node_id} ({peer.hostname})")
    
    def _handle_ack(self, env: Envelope):
        try:
            d = json.loads(env.payload) if env.payload else {}
        except Exception:
            d = {}
        peer = self._get_or_create_peer(env.source)
        peer.hostname = d.get("hostname", "")
        peer.public_key = d.get("public_key", "")
        peer.last_seen = time.time()
        self.routing.add(env.source, env.source, 1.0)
        print(f"[ACK] {peer.node_id} ({peer.hostname})")
    
    def _handle_route(self, env: Envelope):
        try:
            d = json.loads(env.payload)
            for r in d.get("routes", []):
                dest = r["dest"]
                if dest != self.identity.node_id:
                    self.routing.add(dest, env.source, r.get("metric", 1) + 1)
        except Exception:
            pass
    
    def _route_message(self, env: Envelope) -> bool:
        """Route message to destination."""
        dest = env.destination
        
        # Direct peer?
        with self._peers_lock:
            peer = self.peers.get(dest)
        if peer:
            return self._send_to_peer(dest, env)
        
        # Check routing table
        route = self.routing.get(dest)
        if route:
            return self._send_to_peer(route.next_hop, env)
        
        # Broadcast als fallback
        if dest != "*":
            env.destination = "*"
        return self._broadcast_env(env)
    
    def _send_to_peer(self, node_id: str, env: Envelope) -> bool:
        with self._peers_lock:
            peer = self.peers.get(node_id)
        if not peer:
            return False
        
        # Try socket first, then FS
        if self.sock_transport and peer.socket_addr:
            if self.sock_transport.send(env, peer):
                return True
        if self.fs_transport and peer.fs_inbox:
            if self.fs_transport.send(env, peer):
                return True
        
        peer.failures += 1
        return False
    
    def _broadcast(self, msg_type: MsgType, data: dict):
        payload = json.dumps(data).encode() if isinstance(data, dict) else data
        env = Envelope(
            msg_id=str(uuid.uuid4())[:8],
            msg_type=msg_type,
            source=self.identity.node_id,
            destination="*",
            payload=payload
        )
        self._broadcast_env(env)
    
    def _broadcast_env(self, env: Envelope) -> bool:
        sent = False
        with self._peers_lock:
            peers = list(self.peers.values())
        for peer in peers:
            if peer.node_id not in env.hops:
                if self._send_to_peer(peer.node_id, env):
                    sent = True
        return sent
    
    def _touch_peer(self, node_id: str):
        with self._peers_lock:
            if node_id in self.peers:
                self.peers[node_id].last_seen = time.time()
    
    def _get_or_create_peer(self, node_id: str) -> PeerInfo:
        with self._peers_lock:
            if node_id not in self.peers:
                self.peers[node_id] = PeerInfo(node_id=node_id, last_seen=time.time())
            return self.peers[node_id]
    
    def _discovery_loop(self):
        """Discover peers via FS presence files."""
        while _running:
            try:
                if self.fs_transport:
                    for p in self.fs_transport.discover_peers():
                        nid = p.get("node_id")
                        if nid and nid != self.identity.node_id:
                            is_new = nid not in self.peers
                            peer = self._get_or_create_peer(nid)
                            peer.fs_inbox = Path(p.get("inbox", ""))
                            # Register in bridge
                            self.multi_bridge.bridges.get("FS", Bridge("FS", self.fs_transport)).peers.add(nid)
                            # Send handshake to new peer
                            if is_new:
                                print(f"[DISCOVERED] {nid}")
                                self._send_to_peer(nid, Envelope(
                                    msg_id="", msg_type=MsgType.HANDSHAKE,
                                    source=self.identity.node_id, destination=nid,
                                    payload=json.dumps(self.identity.to_public()).encode()
                                ))
            except Exception:
                pass
            time.sleep(5.0)
    
    def _heartbeat_loop(self):
        """Send heartbeats, cleanup dead peers."""
        while _running:
            try:
                now = time.time()
                with self._peers_lock:
                    peers = list(self.peers.items())
                
                for nid, peer in peers:
                    # Send heartbeat
                    self._send_to_peer(nid, Envelope(
                        msg_id="", msg_type=MsgType.HEARTBEAT,
                        source=self.identity.node_id, destination=nid
                    ))
                    # Check timeout
                    if now - peer.last_seen > HEARTBEAT_TIMEOUT:
                        print(f"[DEAD] {nid}")
                        self.routing.remove_via(nid)
                        with self._peers_lock:
                            self.peers.pop(nid, None)
                
                # Announce routes
                routes = [{"dest": self.identity.node_id, "metric": 0}]
                for dest, entry in list(self.routing.routes.items()):
                    if not entry.expired():
                        routes.append({"dest": dest, "metric": entry.metric})
                self._broadcast(MsgType.ROUTE, {"routes": routes})
                
            except Exception:
                pass
            time.sleep(HEARTBEAT_SEC)

# ============================================================================
# LEGACY V1.X COMPATIBILITY LAYER
# ============================================================================

def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

def log_event(cfg: dict, level: str, event: str, src=None, dst=None, 
              status: str = "ok", msg: str = None):
    """JSONL logging (v1.x compatible)."""
    levels = {"debug": 10, "info": 20, "warn": 30, "error": 40}
    if levels.get(level, 20) < levels.get(cfg.get("log_level", "info"), 20):
        return
    entry = {
        "datetime_utc": utc_now(), "level": level, "event": event,
        "src": str(src) if src else None, "dst": str(dst) if dst else None,
        "status": status, "message": msg, "version": VERSION
    }
    LOGFILE.parent.mkdir(parents=True, exist_ok=True)
    with LOGFILE.open("a") as f:
        f.write(json.dumps(entry) + "\n")

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def load_policy() -> dict:
    if CONFIG.exists():
        try:
            cfg = json.loads(CONFIG.read_text())
            for k, v in DEFAULT_POLICY.items():
                cfg.setdefault(k, v)
            return cfg
        except Exception:
            pass
    CONFIG.write_text(json.dumps(DEFAULT_POLICY, indent=2))
    return DEFAULT_POLICY.copy()

def policy_allows(cfg: dict, node: str, path: Path) -> Tuple[bool, str]:
    if node not in cfg.get("trusted_nodes", []):
        return False, f"untrusted:{node}"
    # Check suffixes (including double like .aead.freq)
    allowed = cfg.get("allowed_suffixes", [])
    suffix = "".join(path.suffixes)  # e.g. ".aead.freq"
    if suffix not in allowed and path.suffix not in allowed:
        return False, f"suffix:{suffix}"
    max_mb = cfg.get("max_file_mb", 256)
    if path.exists() and path.stat().st_size > max_mb * 1024 * 1024:
        return False, f"size:{path.stat().st_size}"
    return True, "ok"

def run_core(args: list) -> Tuple[bool, str]:
    try:
        r = subprocess.run(PAXECT_CORE + args, capture_output=True, check=True)
        return True, r.stdout.decode()
    except subprocess.CalledProcessError as e:
        return False, e.stderr.decode()

def run_aead(mode: str, src: Path, dst: Path) -> Tuple[bool, str]:
    """Run AEAD encrypt/decrypt. Returns (success, error_msg)."""
    if not PAXECT_AEAD:
        return True, "no_aead"  # AEAD not configured, skip
    
    args = PAXECT_AEAD + ["--mode", mode]
    if PAXECT_AEAD_PASS:
        args += ["--pass", PAXECT_AEAD_PASS]
    elif PAXECT_AEAD_PASS_FILE:
        args += ["--pass-file", PAXECT_AEAD_PASS_FILE]
    else:
        return False, "no passphrase configured (PAXECT_AEAD_PASS or PAXECT_AEAD_PASS_FILE)"
    
    try:
        with src.open("rb") as inf, dst.open("wb") as outf:
            r = subprocess.run(args, stdin=inf, stdout=outf, stderr=subprocess.PIPE, check=True)
        return True, ""
    except subprocess.CalledProcessError as e:
        dst.unlink(missing_ok=True)
        return False, e.stderr.decode()

def encode_file(cfg: dict, src: Path):
    """Encode: [AEAD encrypt] → Core encode → .freq"""
    # Skip .aead and .freq files
    if src.suffix in (".aead", ".freq"):
        return
    
    # Determine output paths
    if PAXECT_AEAD:
        aead_file = src.with_suffix(".aead")
        freq_file = src.with_suffix(".aead.freq")
    else:
        aead_file = None
        freq_file = src.with_suffix(".freq")
    
    if freq_file.exists():
        return
    
    # Step 1: AEAD encrypt (if configured)
    if PAXECT_AEAD:
        if aead_file.exists():
            pass  # already encrypted
        else:
            ok, err = run_aead("encrypt", src, aead_file)
            if not ok:
                log_event(cfg, "error", "aead_encrypt_error", src, status="error", msg=err)
                time.sleep(BACKOFF_SEC)
                return
            log_event(cfg, "info", "aead_encrypt", src, aead_file)
        encode_src = aead_file
    else:
        encode_src = src
    
    # Step 2: Core encode
    ok, out = run_core(["encode", "-i", str(encode_src), "-o", str(freq_file)])
    if ok:
        sha = sha256_file(freq_file)
        OSLayer.atomic_write(freq_file.with_suffix(".freq.sha256"), (sha + "\n").encode())
        log_event(cfg, "info", "encode", src, freq_file, msg=f"sha256={sha}")
        if cfg.get("auto_delete", True):
            src.unlink(missing_ok=True)
            if aead_file:
                aead_file.unlink(missing_ok=True)
    else:
        log_event(cfg, "error", "encode_error", src, status="error", msg=out)
        time.sleep(BACKOFF_SEC)

def decode_file(cfg: dict, src: Path):
    """Decode: Core decode → [AEAD decrypt] → outbox"""
    # Determine if this is an encrypted file
    is_encrypted = ".aead" in src.suffixes
    
    if is_encrypted:
        # .aead.freq → decode → .aead → decrypt → final
        aead_file = OUTBOX / src.name.replace(".freq", "")
        final_file = OUTBOX / src.name.replace(".aead.freq", "")
    else:
        # .freq → decode → final
        aead_file = None
        final_file = OUTBOX / src.with_suffix("").name
    
    if final_file.exists():
        return
    
    # Verify checksum
    side = src.with_suffix(src.suffix + ".sha256")
    if side.exists():
        want = side.read_text().strip()
        have = sha256_file(src)
        if not hmac.compare_digest(want, have):
            log_event(cfg, "error", "checksum_mismatch", src, status="error")
            return
    
    # Step 1: Core decode
    decode_dst = aead_file if is_encrypted else final_file
    ok, out = run_core(["decode", "-i", str(src), "-o", str(decode_dst)])
    if not ok:
        log_event(cfg, "error", "decode_error", src, status="error", msg=out)
        time.sleep(BACKOFF_SEC)
        return
    
    # Step 2: AEAD decrypt (if encrypted)
    if is_encrypted and PAXECT_AEAD:
        ok, err = run_aead("decrypt", aead_file, final_file)
        if not ok:
            log_event(cfg, "error", "aead_decrypt_error", aead_file, status="error", msg=err)
            aead_file.unlink(missing_ok=True)
            return
        log_event(cfg, "info", "aead_decrypt", aead_file, final_file)
        aead_file.unlink(missing_ok=True)
    
    log_event(cfg, "info", "decode", src, final_file)
    if cfg.get("auto_delete", True):
        src.unlink(missing_ok=True)
        side.unlink(missing_ok=True)

# ============================================================================
# MAIN WITH CLI
# ============================================================================

def _sigterm(_s, _f):
    global _running
    _running = False

def share_mode(identity: "NodeIdentity", cfg: dict) -> str:
    """Start in share mode: genereer code en wacht op connectie."""
    rendezvous = RendezvousClient(RENDEZVOUS_URL, RENDEZVOUS_FILE)
    
    # Bepaal socket adres als socket enabled
    socket_addr = None
    if SOCKET_PORT > 0:
        ip = OSLayer.get_local_ip()
        socket_addr = (ip, SOCKET_PORT)
    
    # Genereer code
    code = generate_wormhole_code()
    wc = WormholeCode(
        code=code,
        node_id=identity.node_id,
        hostname=identity.hostname,
        public_key=identity.public_key,
        socket_addr=socket_addr,
    )
    
    # Publiceer
    if rendezvous.publish(wc):
        print(f"\n{'='*50}")
        print(f"  PAIRING CODE: {code}")
        print(f"{'='*50}")
        print(f"\n  Deel deze code met de andere node.")
        print(f"  De andere node voert uit:")
        print(f"    python3 paxect_link_plugin_v2.py --connect {code}")
        print(f"\n  Code verloopt over {CODE_EXPIRY_SEC // 60} minuten.")
        print(f"  Wachten op connectie...\n")
        return code
    else:
        print("[ERROR] Kon code niet publiceren")
        return ""

def connect_mode(code: str, identity: "NodeIdentity", cfg: dict) -> Optional[WormholeCode]:
    """Connect met een gedeelde code."""
    rendezvous = RendezvousClient(RENDEZVOUS_URL, RENDEZVOUS_FILE)
    
    print(f"\n[CONNECT] Zoeken naar code: {code}")
    
    # Zoek de code
    wc = rendezvous.lookup(code)
    if not wc:
        print(f"[ERROR] Code '{code}' niet gevonden of verlopen")
        return None
    
    if wc.is_expired():
        print(f"[ERROR] Code '{code}' is verlopen")
        return None
    
    print(f"[FOUND] Node gevonden:")
    print(f"  - Node ID  : {wc.node_id}")
    print(f"  - Hostname : {wc.hostname}")
    if wc.socket_addr:
        print(f"  - Socket   : {wc.socket_addr[0]}:{wc.socket_addr[1]}")
    
    # Voeg toe aan trusted_nodes en policy
    if wc.node_id not in cfg.get("trusted_nodes", []):
        cfg["trusted_nodes"].append(wc.node_id)
    if wc.hostname not in cfg.get("trusted_nodes", []):
        cfg["trusted_nodes"].append(wc.hostname)
    
    # Sla bijgewerkte policy op
    CONFIG.write_text(json.dumps(cfg, indent=2))
    print(f"[POLICY] {wc.node_id} toegevoegd aan trusted_nodes")
    
    # Publiceer onze eigen info als response
    our_wc = WormholeCode(
        code=code + "-accept",
        node_id=identity.node_id,
        hostname=identity.hostname,
        public_key=identity.public_key,
        socket_addr=(OSLayer.get_local_ip(), SOCKET_PORT) if SOCKET_PORT > 0 else None,
    )
    rendezvous.publish(our_wc)
    
    # Cleanup originele code
    rendezvous.remove(code)
    
    print(f"\n[SUCCESS] Verbonden met {wc.hostname}!")
    return wc

def wait_for_accept(code: str, identity: "NodeIdentity", cfg: dict, timeout: int = 300) -> Optional[WormholeCode]:
    """Wacht tot iemand onze code accepteert."""
    rendezvous = RendezvousClient(RENDEZVOUS_URL, RENDEZVOUS_FILE)
    accept_code = code + "-accept"
    start = time.time()
    
    while time.time() - start < timeout:
        wc = rendezvous.lookup(accept_code)
        if wc:
            print(f"\n[ACCEPTED] Verbonden met {wc.hostname}!")
            
            # Voeg toe aan policy
            if wc.node_id not in cfg.get("trusted_nodes", []):
                cfg["trusted_nodes"].append(wc.node_id)
            if wc.hostname not in cfg.get("trusted_nodes", []):
                cfg["trusted_nodes"].append(wc.hostname)
            CONFIG.write_text(json.dumps(cfg, indent=2))
            
            # Cleanup
            rendezvous.remove(code)
            rendezvous.remove(accept_code)
            
            return wc
        
        time.sleep(2)
    
    print("\n[TIMEOUT] Geen connectie ontvangen")
    rendezvous.remove(code)
    return None

def run_normal_mode(cfg: dict):
    """Run in normale watch mode."""
    global _running
    
    print(f"=== PAXECT Link Plugin v{VERSION} ===")
    print(f"Script  : {Path(__file__).resolve()}")
    print(f"Time    : {utc_now()}")
    print(f"Inbox   : {INBOX.resolve()}")
    print(f"Outbox  : {OUTBOX.resolve()}")
    print(f"Shared  : {SHARED_DIR.resolve()}")
    print()
    
    INBOX.mkdir(parents=True, exist_ok=True)
    OUTBOX.mkdir(parents=True, exist_ok=True)
    
    # Single instance lock
    try:
        fd = os.open(LOCKFILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "w") as f:
            f.write(f"{os.getpid()}\n")
    except FileExistsError:
        print("[LINK] Another instance running. Exit.")
        return
    
    signal.signal(signal.SIGINT, _sigterm)
    signal.signal(signal.SIGTERM, _sigterm)
    
    try:
        # Start router (v2.0)
        router = LinkRouter(cfg)
        router.start()
        
        # Data callback: relay ontvangen data naar outbox
        def on_data(env: Envelope):
            if env.payload:
                ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                out = OUTBOX / f"relay_{env.source}_{ts}.bin"
                out.write_bytes(env.payload)paxect_link_plugin_v2.py
                log_event(cfg, "info", "relay_recv", env.source, out)
        
        router.set_data_callback(on_data)
        
        log_event(cfg, "info", "startup", INBOX, OUTBOX, msg=f"v{VERSION}")
        print("[LINK] Watching... (Ctrl+C to stop)\n")
        
        node = OSLayer.node_name
        
        while _running:
            # V1.x compatible: local inbox processing
            for f in INBOX.iterdir():
                if not f.is_file() or f.name.startswith(".") or f.suffix in (".part", ".tmp"):
                    continue
                ok, reason = policy_allows(cfg, node, f)
                if not ok:
                    log_event(cfg, "warn", "policy_block", f, status="warn", msg=reason)
                    continue
                if f.suffix == ".freq":
                    decode_file(cfg, f)
                else:
                    encode_file(cfg, f)
            
            time.sleep(POLL_INTERVAL)
        
        print("\n[LINK] Stopping...")
        router.stop()
        
    finally:
        log_event(cfg, "info", "shutdown", status="ok")
        LOCKFILE.unlink(missing_ok=True)

def main():
    global _running
    
    parser = argparse.ArgumentParser(
        description="PAXECT Link Plugin v2.1 - Multi-Bridge Relay with Wormhole Discovery",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Voorbeelden:
  # Normaal draaien (watch mode):
  python3 paxect_link_plugin_v2.py

  # Deel een pairing code:
  python3 paxect_link_plugin_v2.py --share

  # Verbind met een code:
  python3 paxect_link_plugin_v2.py --connect 7-tiger-mountain

  # Start rendezvous server:
  python3 paxect_link_plugin_v2.py --rendezvous-server --port 9878
"""
    )
    
    parser.add_argument("--share", action="store_true",
                        help="Genereer pairing code en wacht op connectie")
    parser.add_argument("--connect", metavar="CODE",
                        help="Verbind met een pairing code")
    parser.add_argument("--rendezvous-server", action="store_true",
                        help="Start als rendezvous server")
    parser.add_argument("--port", type=int, default=9878,
                        help="Port voor rendezvous server (default: 9878)")
    parser.add_argument("--list-peers", action="store_true",
                        help="Toon bekende peers")
    parser.add_argument("--version", action="version", version=f"PAXECT Link v{VERSION}")
    
    args = parser.parse_args()
    
    # Load config and identity
    cfg = load_policy()
    identity = NodeIdentity.load_or_create(IDENTITY_FILE)
    
    if args.rendezvous_server:
        # Run as rendezvous server
        print(f"=== PAXECT Rendezvous Server ===")
        server = RendezvousServer("0.0.0.0", args.port)
        server.start()
        print(f"Server draait op port {args.port}")
        print("Ctrl+C om te stoppen...")
        
        signal.signal(signal.SIGINT, _sigterm)
        signal.signal(signal.SIGTERM, _sigterm)
        
        while _running:
            time.sleep(1)
        
        server.stop()
        return
    
    if args.share:
        # Share mode
        INBOX.mkdir(parents=True, exist_ok=True)
        OUTBOX.mkdir(parents=True, exist_ok=True)
        
        code = share_mode(identity, cfg)
        if code:
            # Wacht op accept, dan start normal mode
            peer = wait_for_accept(code, identity, cfg)
            if peer:
                print(f"\n[START] Starten in normal mode...\n")
                run_normal_mode(cfg)
        return
    
    if args.connect:
        # Connect mode
        INBOX.mkdir(parents=True, exist_ok=True)
        OUTBOX.mkdir(parents=True, exist_ok=True)
        
        peer = connect_mode(args.connect, identity, cfg)
        if peer:
            print(f"\n[START] Starten in normal mode...\n")
            run_normal_mode(cfg)
        return
    
    if args.list_peers:
        # List known peers
        print(f"=== Bekende Peers ===")
        print(f"Trusted nodes: {cfg.get('trusted_nodes', [])}")
        return
    
    # Default: normal mode
    run_normal_mode(cfg)

if __name__ == "__main__":
    main()
