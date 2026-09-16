from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        if key.strip():
            values[key.strip()] = value
    return values


def _default_binance_env() -> Path:
    # alpha-lab-os/src/alpha_lab_os/config.py -> workspace root -> sibling project
    return Path(__file__).resolve().parents[3] / "web3-arb-lab" / ".env"


def load_local_env(path: str | None = None) -> Path | None:
    """Load variables without printing secrets or overwriting the process env."""
    configured = path or os.getenv("BINANCE_ENV_FILE", "").strip()
    env_path = Path(configured) if configured else _default_binance_env()
    values = _read_env_file(env_path)
    for key, value in values.items():
        os.environ.setdefault(key, value)
    return env_path if env_path.exists() else None


@dataclass(frozen=True)
class Settings:
    api_key: str
    secret_key: str
    base_url: str = "https://web3.binance.com/build"
    qps: float = 5.0
    recv_window_ms: int = 5000
    timeout_s: float = 15.0
    credentials_file: str | None = None

    @classmethod
    def from_env(cls, require_credentials: bool = True) -> "Settings":
        env_file = load_local_env()
        api_key = os.getenv("OC_API_KEY", "")
        secret_key = os.getenv("OC_SECRET_KEY", "")
        if require_credentials and (not api_key or not secret_key):
            raise RuntimeError("Missing Binance Web3 credentials; set BINANCE_ENV_FILE or OC_API_KEY/OC_SECRET_KEY locally.")
        qps = float(os.getenv("BINANCE_WEB3_QPS", "5"))
        if qps <= 0 or qps > 50:
            raise ValueError("BINANCE_WEB3_QPS must be in (0, 50]")
        return cls(
            api_key=api_key,
            secret_key=secret_key,
            base_url=os.getenv("BINANCE_WEB3_BASE_URL", cls.base_url).rstrip("/"),
            qps=qps,
            recv_window_ms=int(os.getenv("BINANCE_WEB3_RECV_WINDOW_MS", "5000")),
            timeout_s=float(os.getenv("BINANCE_WEB3_TIMEOUT_S", "15")),
            credentials_file=str(env_file) if env_file else None,
        )
