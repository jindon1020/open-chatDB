import json
import os
import uuid
import threading
from config import Config

# Lazy imports to avoid hard dependency if a driver isn't installed
_pymysql = None
_pymongo = None
_elasticsearch = None
_sshtunnel = None


def _import_pymysql():
    global _pymysql
    if _pymysql is None:
        import pymysql
        _pymysql = pymysql
    return _pymysql


def _import_pymongo():
    global _pymongo
    if _pymongo is None:
        import pymongo
        _pymongo = pymongo
    return _pymongo


def _import_elasticsearch():
    global _elasticsearch
    if _elasticsearch is None:
        import elasticsearch
        _elasticsearch = elasticsearch
    return _elasticsearch


def _import_sshtunnel():
    global _sshtunnel
    if _sshtunnel is None:
        import sshtunnel
        _sshtunnel = sshtunnel
    return _sshtunnel


class ConnectionManager:
    def __init__(self):
        self._lock = threading.Lock()
        # id -> {"config": {...}, "client": <conn>, "tunnel": <SSHTunnelForwarder|None>}
        self._active: dict = {}
        self._configs: list[dict] = self._load_configs()

    # ---- persistence ----
    def _load_configs(self) -> list[dict]:
        path = Config.CONNECTIONS_FILE
        if os.path.exists(path):
            with open(path, "r") as f:
                return json.load(f)
        return []

    def _save_configs(self):
        os.makedirs(os.path.dirname(Config.CONNECTIONS_FILE), exist_ok=True)
        with open(Config.CONNECTIONS_FILE, "w") as f:
            json.dump(self._configs, f, indent=2, ensure_ascii=False)

    # ---- CRUD ----
    def list_configs(self) -> list[dict]:
        return self._configs

    def get_config(self, conn_id: str) -> dict | None:
        for c in self._configs:
            if c["id"] == conn_id:
                return c
        return None

    def save_config(self, cfg: dict) -> dict:
        if not cfg.get("id"):
            cfg["id"] = uuid.uuid4().hex[:12]
        existing = self.get_config(cfg["id"])
        if existing:
            existing.update(cfg)
        else:
            self._configs.append(cfg)
        self._save_configs()
        return cfg

    def delete_config(self, conn_id: str):
        self.disconnect(conn_id)
        self._configs = [c for c in self._configs if c["id"] != conn_id]
        self._save_configs()

    # ---- connect / disconnect ----
    def _open_ssh_tunnel(self, cfg: dict):
        ssh = cfg.get("ssh")
        if not ssh or not ssh.get("host"):
            return None
        sshtunnel = _import_sshtunnel()
        ssh_kwargs = {
            "ssh_address_or_host": (ssh["host"], int(ssh.get("port", 22))),
            "ssh_username": ssh.get("username", ""),
            "remote_bind_address": (cfg.get("host", "127.0.0.1"), int(cfg.get("port", 3306))),
        }
        if ssh.get("password"):
            ssh_kwargs["ssh_password"] = ssh["password"]
        if ssh.get("key_file"):
            ssh_kwargs["ssh_pkey"] = ssh["key_file"]
        tunnel = sshtunnel.SSHTunnelForwarder(**ssh_kwargs)
        tunnel.start()
        return tunnel

    def connect(self, conn_id: str) -> dict:
        with self._lock:
            if conn_id in self._active:
                return {"status": "already_connected"}
            cfg = self.get_config(conn_id)
            if not cfg:
                raise ValueError(f"Connection config {conn_id} not found")

            tunnel = self._open_ssh_tunnel(cfg)
            host = "127.0.0.1" if tunnel else cfg.get("host", "127.0.0.1")
            port = tunnel.local_bind_port if tunnel else int(cfg.get("port", 3306))

            db_type = cfg.get("type", "mysql")
            client = None

            if db_type == "mysql":
                pymysql = _import_pymysql()
                client = pymysql.connect(
                    host=host,
                    port=port,
                    user=cfg.get("user", "root"),
                    password=cfg.get("password", ""),
                    database=cfg.get("database", ""),
                    charset="utf8mb4",
                    cursorclass=pymysql.cursors.DictCursor,
                    autocommit=True,
                )
            elif db_type == "mongodb":
                pymongo = _import_pymongo()
                uri = cfg.get("uri")
                if uri:
                    client = pymongo.MongoClient(uri)
                else:
                    client = pymongo.MongoClient(
                        host=host,
                        port=port,
                        username=cfg.get("user") or None,
                        password=cfg.get("password") or None,
                    )
            elif db_type == "elasticsearch":
                es = _import_elasticsearch()
                scheme = cfg.get("scheme", "http")
                url = f"{scheme}://{host}:{port}"
                kwargs = {}
                if cfg.get("user"):
                    kwargs["basic_auth"] = (cfg["user"], cfg.get("password", ""))
                if cfg.get("api_key"):
                    kwargs["api_key"] = cfg["api_key"]
                if cfg.get("verify_certs") is False:
                    kwargs["verify_certs"] = False
                client = es.Elasticsearch(url, **kwargs)
            else:
                raise ValueError(f"Unsupported db type: {db_type}")

            self._active[conn_id] = {
                "config": cfg,
                "client": client,
                "tunnel": tunnel,
            }
            return {"status": "connected"}

    def disconnect(self, conn_id: str):
        with self._lock:
            entry = self._active.pop(conn_id, None)
            if not entry:
                return
            client = entry["client"]
            db_type = entry["config"].get("type", "mysql")
            try:
                if db_type == "mysql":
                    client.close()
                elif db_type == "mongodb":
                    client.close()
                elif db_type == "elasticsearch":
                    client.close()
            except Exception:
                pass
            tunnel = entry.get("tunnel")
            if tunnel:
                try:
                    tunnel.stop()
                except Exception:
                    pass

    def get_client(self, conn_id: str):
        entry = self._active.get(conn_id)
        if not entry:
            raise ValueError(f"Connection {conn_id} is not active. Connect first.")
        return entry["client"]

    def get_db_type(self, conn_id: str) -> str:
        entry = self._active.get(conn_id)
        if entry:
            return entry["config"].get("type", "mysql")
        cfg = self.get_config(conn_id)
        if cfg:
            return cfg.get("type", "mysql")
        raise ValueError(f"Connection {conn_id} not found")

    def is_connected(self, conn_id: str) -> bool:
        return conn_id in self._active

    def test_connection(self, cfg: dict) -> dict:
        """Test a connection without persisting it."""
        temp_id = "__test__"
        cfg_copy = {**cfg, "id": temp_id}
        # temporarily add config
        self._configs.append(cfg_copy)
        try:
            self.connect(temp_id)
            self.disconnect(temp_id)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}
        finally:
            self._configs = [c for c in self._configs if c["id"] != temp_id]


# Singleton
manager = ConnectionManager()
