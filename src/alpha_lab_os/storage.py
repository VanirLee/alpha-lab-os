from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable, Mapping


SCHEMA = """
CREATE TABLE IF NOT EXISTS api_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL,
  tier TEXT NOT NULL,
  endpoint TEXT NOT NULL,
  method TEXT NOT NULL,
  requested_at_ms INTEGER NOT NULL,
  completed_at_ms INTEGER NOT NULL,
  http_status INTEGER,
  business_code INTEGER,
  latency_ms REAL,
  transport_error TEXT,
  retry_after TEXT,
  params_json TEXT,
  body_json TEXT,
  response_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_api_events_run ON api_events(run_id);

CREATE TABLE IF NOT EXISTS market_state (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL,
  observed_at_ms INTEGER NOT NULL,
  chain TEXT NOT NULL,
  token TEXT NOT NULL,
  symbol TEXT,
  price REAL,
  price_change_5m REAL,
  price_change_1h REAL,
  volume_5m REAL,
  buy_volume_5m REAL,
  sell_volume_5m REAL,
  txs_5m REAL,
  liquidity REAL,
  market_cap REAL,
  holders REAL,
  raw_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_market_token_time ON market_state(chain, token, observed_at_ms);

CREATE TABLE IF NOT EXISTS token_state (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL,
  observed_at_ms INTEGER NOT NULL,
  chain TEXT NOT NULL,
  token TEXT NOT NULL,
  state_type TEXT NOT NULL,
  raw_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_token_state_time ON token_state(chain, token, observed_at_ms);

CREATE TABLE IF NOT EXISTS candles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL,
  chain TEXT NOT NULL,
  token TEXT NOT NULL,
  bar TEXT NOT NULL,
  candle_ts_ms INTEGER,
  open REAL, high REAL, low REAL, close REAL, volume REAL, trade_count REAL,
  raw_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_candles_token_time ON candles(chain, token, candle_ts_ms);

CREATE TABLE IF NOT EXISTS quotes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL,
  observed_at_ms INTEGER NOT NULL,
  chain TEXT NOT NULL,
  from_token TEXT NOT NULL,
  to_token TEXT NOT NULL,
  amount_in TEXT NOT NULL,
  amount_out TEXT,
  vendor TEXT,
  quote_id TEXT,
  trade_fee TEXT,
  gas_fee TEXT,
  price_impact_percent REAL,
  route_count INTEGER,
  route_spread_bps REAL,
  latency_ms REAL,
  raw_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_quotes_pair_time ON quotes(chain, from_token, to_token, observed_at_ms);

CREATE TABLE IF NOT EXISTS trades (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL,
  observed_at_ms INTEGER NOT NULL,
  chain TEXT NOT NULL,
  token TEXT NOT NULL,
  trade_ts_ms INTEGER,
  wallet TEXT,
  side TEXT,
  amount TEXT,
  price REAL,
  tag TEXT,
  raw_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_trades_token_time ON trades(chain, token, trade_ts_ms);
"""


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)


def _number(value: Any) -> float | None:
    try:
        return None if value in (None, "") else float(value)
    except (TypeError, ValueError):
        return None


class Store:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "Store":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    def add_api_event(self, run_id: str, tier: str, endpoint: str, method: str, started_ms: int, response: Any, params: Any = None, body: Any = None) -> None:
        completed_ms = started_ms + int(float(getattr(response, "latency_ms", 0) or 0))
        self.conn.execute(
            "INSERT INTO api_events(run_id,tier,endpoint,method,requested_at_ms,completed_at_ms,http_status,business_code,latency_ms,transport_error,retry_after,params_json,body_json,response_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (run_id, tier, endpoint, method, started_ms, completed_ms, getattr(response, "http_status", None), getattr(response, "business_code", None), getattr(response, "latency_ms", None), getattr(response, "transport_error", None), getattr(response, "retry_after", None), _json(params) if params is not None else None, _json(body) if body is not None else None, _json(getattr(response, "body", None))),
        )

    def add_market_rows(self, run_id: str, observed_at_ms: int, rows: Iterable[Mapping[str, Any]]) -> int:
        count = 0
        for item in rows:
            self.conn.execute(
                "INSERT INTO market_state(run_id,observed_at_ms,chain,token,symbol,price,price_change_5m,price_change_1h,volume_5m,buy_volume_5m,sell_volume_5m,txs_5m,liquidity,market_cap,holders,raw_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (run_id, observed_at_ms, str(item.get("binanceChainId", item.get("chain", ""))), str(item.get("tokenContractAddress", item.get("token", ""))), item.get("symbol"), _number(item.get("price")), _number(item.get("priceChange5M")), _number(item.get("priceChange1H")), _number(item.get("volume5M")), _number(item.get("buyVolume5M")), _number(item.get("sellVolume5M")), _number(item.get("txs5M")), _number(item.get("liquidity")), _number(item.get("marketCap")), _number(item.get("holders")), _json(item)),
            )
            count += 1
        return count

    def add_token_state(self, run_id: str, observed_at_ms: int, token: Mapping[str, Any], state_type: str, raw: Any) -> None:
        self.conn.execute("INSERT INTO token_state(run_id,observed_at_ms,chain,token,state_type,raw_json) VALUES(?,?,?,?,?,?)", (run_id, observed_at_ms, str(token["chain"]), str(token["token"]), state_type, _json(raw)))

    def add_candles(self, run_id: str, token: Mapping[str, Any], bar: str, rows: Iterable[Any]) -> int:
        count = 0
        for row in rows:
            if not isinstance(row, (list, tuple)):
                continue
            values = list(row) + [None] * 7
            self.conn.execute("INSERT INTO candles(run_id,chain,token,bar,candle_ts_ms,open,high,low,close,volume,trade_count,raw_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", (run_id, str(token["chain"]), str(token["token"]), bar, int(float(values[5])) if values[5] is not None else None, *[_number(value) for value in values[:5]], _number(values[6]), _json(row)))
            count += 1
        return count

    def add_quote_rows(self, run_id: str, observed_at_ms: int, pair: Mapping[str, Any], amount: str, response: Any, routes: Iterable[Mapping[str, Any]]) -> int:
        route_list = [row for row in routes if isinstance(row, Mapping)]
        outputs = [_number(row.get("toTokenAmount")) for row in route_list]
        outputs = [value for value in outputs if value is not None and value > 0]
        spread = ((max(outputs) / min(outputs)) - 1) * 10000 if len(outputs) >= 2 else None
        for route in route_list:
            self.conn.execute("INSERT INTO quotes(run_id,observed_at_ms,chain,from_token,to_token,amount_in,amount_out,vendor,quote_id,trade_fee,gas_fee,price_impact_percent,route_count,route_spread_bps,latency_ms,raw_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (run_id, observed_at_ms, str(pair["chain"]), str(pair["from_token"]), str(pair["to_token"]), str(amount), str(route.get("toTokenAmount")) if route.get("toTokenAmount") is not None else None, route.get("vendorName"), route.get("quoteId"), route.get("tradeFee"), route.get("estimateGasFee"), _number(route.get("priceImpactPercent")), len(route_list), spread, getattr(response, "latency_ms", None), _json(route)))
        if not route_list:
            self.conn.execute("INSERT INTO quotes(run_id,observed_at_ms,chain,from_token,to_token,amount_in,route_count,latency_ms,raw_json) VALUES(?,?,?,?,?,?,?,?,?)", (run_id, observed_at_ms, str(pair["chain"]), str(pair["from_token"]), str(pair["to_token"]), str(amount), 0, getattr(response, "latency_ms", None), _json(getattr(response, "body", None))))
        return len(route_list)

    def add_trades(self, run_id: str, observed_at_ms: int, token: Mapping[str, Any], raw: Any) -> int:
        rows = raw if isinstance(raw, list) else raw.get("data", raw.get("trades", [])) if isinstance(raw, Mapping) else []
        if isinstance(rows, Mapping):
            rows = rows.get("list", rows.get("tradeList", []))
        count = 0
        for row in rows if isinstance(rows, list) else []:
            if not isinstance(row, Mapping):
                continue
            self.conn.execute("INSERT INTO trades(run_id,observed_at_ms,chain,token,trade_ts_ms,wallet,side,amount,price,tag,raw_json) VALUES(?,?,?,?,?,?,?,?,?,?,?)", (run_id, observed_at_ms, str(token["chain"]), str(token["token"]), int(float(row.get("time", row.get("tradeTime", row.get("timestamp", 0))) or 0)) or None, row.get("walletAddress", row.get("address", row.get("wallet"))), row.get("side", row.get("direction")), str(row.get("amount")) if row.get("amount") is not None else None, _number(row.get("price")), row.get("tag", row.get("tagType")), _json(row)))
            count += 1
        return count

    def commit(self) -> None:
        self.conn.commit()

    def query(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        return [dict(row) for row in self.conn.execute(sql, params).fetchall()]

    def counts(self) -> dict[str, int]:
        return {table: int(self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]) for table in ("api_events", "market_state", "token_state", "candles", "quotes", "trades")}

    def panel_rows(self) -> list[dict[str, Any]]:
        return self.query("SELECT * FROM market_state ORDER BY observed_at_ms, chain, token")

