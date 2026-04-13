'''import mysql.connector
from typing import Optional, Dict

# ──────────────────────────────────────────────────────────────
# Per-session connection store  (keyed by session_id)
# Each browser tab / user gets its own DB credentials.
# ──────────────────────────────────────────────────────────────
_session_configs: Dict[str, dict] = {}


def set_connection_config(
    session_id: str,
    host: str,
    user: str,
    password: str,
    database: str,
    port: int = 3306,
):
    """Store DB credentials for a specific session."""
    _session_configs[session_id] = {
        "host": host,
        "user": user,
        "password": password,
        "database": database,
        "port": port,
    }


def get_connection(session_id: str):
    """Return a fresh MySQL connection for the given session."""
    cfg = _session_configs.get(session_id)
    if cfg is None:
        raise ConnectionError(
            "No database connected for this session. Please call /connect first."
        )
    return mysql.connector.connect(**cfg)


def get_config(session_id: str) -> Optional[dict]:
    """Return config for a session (password excluded)."""
    cfg = _session_configs.get(session_id)
    if cfg is None:
        return None
    return {k: v for k, v in cfg.items() if k != "password"}


def clear_session(session_id: str):
    """Remove a session's stored credentials."""
    _session_configs.pop(session_id, None)


def test_connection(
    host: str, user: str, password: str, database: str, port: int = 3306
) -> bool:
    """Test credentials before saving them."""
    try:
        conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            port=port,
            connect_timeout=5,
        )
        conn.close()
        return True
    except Exception as e:
        raise ConnectionError(str(e))
'''
import mysql.connector
from typing import Optional, Dict
import threading

# Thread-safe store
_session_configs: Dict[str, dict] = {}
lock = threading.Lock()


def set_connection_config(
    session_id: str,
    host: str,
    user: str,
    password: str,
    database: str,
    port: int = 3306,
):
    """Store DB credentials for a specific session."""
    with lock:
        _session_configs[session_id] = {
            "host": host,
            "user": user,
            "password": password,
            "database": database,
            "port": port,
        }


def get_connection(session_id: str):
    """Create NEW connection every time (no caching)."""
    with lock:
        cfg = _session_configs.get(session_id)

    if cfg is None:
        raise ConnectionError(
            "No database connected for this session. Please call /connect first."
        )

    try:
        return mysql.connector.connect(
            host=cfg["host"],
            user=cfg["user"],
            password=cfg["password"],
            database=cfg["database"],
            port=cfg["port"],
            connection_timeout=5,
            autocommit=True,
        )
    except Exception as e:
        raise ConnectionError(f"DB connection failed: {str(e)}")


def get_config(session_id: str) -> Optional[dict]:
    with lock:
        cfg = _session_configs.get(session_id)

    if cfg is None:
        return None

    return {k: v for k, v in cfg.items() if k != "password"}


def clear_session(session_id: str):
    with lock:
        _session_configs.pop(session_id, None)


def test_connection(
    host: str, user: str, password: str, database: str, port: int = 3306
) -> bool:
    try:
        conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            port=port,
            connection_timeout=5,
        )
        conn.close()
        return True
    except Exception as e:
        raise ConnectionError(str(e))