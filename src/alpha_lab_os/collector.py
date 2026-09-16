from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Mapping

from . import api
from .storage import Store


def load_config(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("config must be a JSON object")
    tiers = value.get("tiers", {})
    if not isinstance(tiers, Mapping) or not tiers.get("radar"):
        raise ValueError("config.tiers.radar must contain at least one token")
    return value


def _token(item: Mapping[str, Any]) -> dict[str, str]:
    return {"chain": str(item["chain"]), "token": str(item["token"]), "symbol": str(item.get("symbol", ""))}


def _record(store: Store, run_id: str, tier: str, endpoint: str, method: str, started: int, response: Any, params: Any = None, body: Any = None) -> None:
    store.add_api_event(run_id, tier, endpoint, method, started, response, params=params, body=body)


def collect(client: Any, config: Mapping[str, Any], db_path: str | Path) -> dict[str, Any]:
    run_id = f"run-{uuid.uuid4().hex[:12]}"
    started_all = int(time.time() * 1000)
    tiers = config.get("tiers", {})
    options = config.get("options", {})
    radar = [_token(item) for item in tiers.get("radar", [])]
    research = [_token(item) for item in tiers.get("research", radar)]
    active = [dict(item) for item in tiers.get("active", [])]
    summary = {"run_id": run_id, "started_at_ms": started_all, "status": "OK", "errors": [], "collected": {"market": 0, "advanced": 0, "candles": 0, "quotes": 0, "trades": 0}}
    with Store(db_path) as store:
        observed = int(time.time() * 1000)
        for offset in range(0, len(radar), 100):
            batch = radar[offset:offset + 100]
            try:
                request_started = int(time.time() * 1000)
                response, rows = api.price_info(client, batch)
                request_body = [{"binanceChainId": item["chain"], "tokenContractAddress": item["token"]} for item in batch]
                _record(store, run_id, "radar", api.PRICE_INFO, "POST", request_started, response, body=request_body)
                if response.ok:
                    summary["collected"]["market"] += store.add_market_rows(run_id, observed, rows)
                else:
                    summary["errors"].append(f"price-info batch {offset // 100 + 1}: http={response.http_status} code={response.business_code}")
            except Exception as exc:
                summary["errors"].append(f"price-info batch {offset // 100 + 1}: {type(exc).__name__}: {exc}")

        for token in research:
            if options.get("include_advanced", True):
                request_started = int(time.time() * 1000)
                try:
                    response, data = api.advanced_info(client, token)
                    _record(store, run_id, "research", api.ADVANCED_INFO, "GET", request_started, response, params={"binanceChainId": token["chain"], "tokenContractAddress": token["token"]})
                    if response.ok:
                        store.add_token_state(run_id, observed, token, "advanced_info", data)
                        summary["collected"]["advanced"] += 1
                except Exception as exc:
                    summary["errors"].append(f"advanced-info {token['symbol']}: {type(exc).__name__}: {exc}")
            request_started = int(time.time() * 1000)
            try:
                response, rows = api.candles(client, token, str(options.get("candles_bar", "1m")), int(options.get("candles_limit", 60)))
                _record(store, run_id, "research", api.CANDLES, "GET", request_started, response, params={"binanceChainId": token["chain"], "tokenContractAddress": token["token"]})
                if response.ok:
                    summary["collected"]["candles"] += store.add_candles(run_id, token, str(options.get("candles_bar", "1m")), rows)
            except Exception as exc:
                summary["errors"].append(f"candles {token['symbol']}: {type(exc).__name__}: {exc}")

        for pair in active:
            for amount in pair.get("amounts", []):
                request_started = int(time.time() * 1000)
                try:
                    response, routes = api.quote(client, pair, str(amount))
                    _record(store, run_id, "active", api.QUOTE, "GET", request_started, response, params={"binanceChainId": pair["chain"], "amount": str(amount), "fromTokenAddress": pair["from_token"], "toTokenAddress": pair["to_token"]})
                    summary["collected"]["quotes"] += store.add_quote_rows(run_id, int(time.time() * 1000), pair, str(amount), response, routes)
                except Exception as exc:
                    summary["errors"].append(f"quote {pair.get('id', 'pair')}: {type(exc).__name__}: {exc}")
            if options.get("include_trades", False):
                token = {"chain": str(pair["chain"]), "token": str(pair["to_token"]), "symbol": str(pair.get("to_symbol", ""))}
                request_started = int(time.time() * 1000)
                try:
                    response, data = api.token_trades(client, token, int(options.get("trades_limit", 100)))
                    _record(store, run_id, "active", api.TRADES, "GET", request_started, response, params={"binanceChainId": token["chain"], "tokenContractAddress": token["token"]})
                    if response.ok:
                        summary["collected"]["trades"] += store.add_trades(run_id, int(time.time() * 1000), token, data)
                except Exception as exc:
                    summary["errors"].append(f"trades {token['symbol']}: {type(exc).__name__}: {exc}")

        summary["status"] = "OK" if not summary["errors"] else "PARTIAL"
        summary["finished_at_ms"] = int(time.time() * 1000)
        store.commit()
        summary["db_counts"] = store.counts()
    return summary


def dry_run_plan(config: Mapping[str, Any]) -> dict[str, Any]:
    tiers = config.get("tiers", {})
    options = config.get("options", {})
    radar = len(tiers.get("radar", []))
    research = len(tiers.get("research", tiers.get("radar", [])))
    active = sum(len(pair.get("amounts", [])) for pair in tiers.get("active", []))
    return {"status": "DRY_RUN", "network_called": False, "radar_tokens": radar, "research_tokens": research, "quote_sizes": active, "planned_endpoints": {"price_info": (radar + 99) // 100, "candles": research, "advanced_info": research if options.get("include_advanced", True) else 0, "quotes": active, "trades": len(tiers.get("active", [])) if options.get("include_trades", False) else 0}, "safety": "read_only; no signature, approval, swap build, simulation, or broadcast"}
